import os
import time
from pathlib import Path

import imageio_ffmpeg
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    FetchedTranscript,
    TranscriptsDisabled,
    NoTranscriptFound,
)
from youtube_transcript_api.proxies import GenericProxyConfig, WebshareProxyConfig
from yt_dlp import YoutubeDL

from src.config.logger import Logger
from src.config.settings import settings
from src.domain.exception.youtube_exceptions import (
    YoutubeTranscriptNotFoundException,
    YoutubeTranscriptsDisabledException,
    YoutubeVideoPrivateException,
    YoutubeVideoUnplayableException,
    YoutubeNetworkException,
)
from src.domain.interfaces.extractors.youtube_extractor_interface import (
    IYoutubeExtractor,
)
from src.infrastructure.extractors.models.youtube_metadata_dto import YoutubeMetadataDTO

logger = Logger()


class YoutubeExtractor(IYoutubeExtractor):
    """Extracts metadata, transcripts and downloads audio from YouTube videos."""

    def __init__(self, video_id: str | None = None, language: str = "pt"):
        self.video_id = video_id
        self.video_url = (
            f"https://www.youtube.com/watch?v={video_id}" if video_id else None
        )
        self.language = language
        self._ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    def _get_common_ydl_opts(self, quiet: bool = True) -> dict:
        """Centralized configuration for yt-dlp options."""
        opts: dict = {
            "logger": logger,
            "quiet": quiet,
            "no_warnings": quiet,
            "nocheckcertificate": True,
            "geo_bypass": True,
            # Force IPv4 to avoid "Connection refused" on some network configurations
            "source_address": "0.0.0.0",
            # Mimic a modern browser to avoid blocks
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://www.google.com/",
            },
            # Internal yt-dlp retries
            "retries": 10,
            "fragment_retries": 10,
            "retry_sleep_functions": {"http": lambda n: 5 * 2**n},
            # Mimic web-based player
            "extractor_args": {"youtube": {"player_client": ["web"]}},
        }

        if settings.youtube.proxy_enabled:
            proxy = settings.youtube.proxy_url
            if (
                not proxy
                and settings.youtube.webshare_username
                and settings.youtube.webshare_username.strip()
                and settings.youtube.webshare_password
                and settings.youtube.webshare_password.strip()
            ):
                proxy = f"http://{settings.youtube.webshare_username}:{settings.youtube.webshare_password}@p.webshare.io:80"

            if proxy:
                opts["proxy"] = proxy

        return opts

    def _run_with_retry(self, action, max_retries: int = 3, initial_delay: int = 5):
        """Standard retry wrapper for YouTube operations."""
        last_exception: Exception = Exception("YouTube operation failed after retries")
        for attempt in range(max_retries):
            try:
                return action()
            except Exception as e:
                last_exception = e
                # Check for specific fatal errors that shouldn't be retried
                err_msg = str(e)
                if any(
                    x in err_msg for x in ["Private video", "not available", "Sign in"]
                ):
                    logger.error(f"Fatal YouTube error: {e}")
                    raise

                delay = initial_delay * (2**attempt)
                logger.warning(
                    f"YouTube action failed (attempt {attempt + 1}/{max_retries}). Retrying in {delay}s...",
                    context={"error": err_msg},
                )
                time.sleep(delay)
        raise last_exception

    def extract_metadata(self, url: str | None = None) -> YoutubeMetadataDTO:
        """Extracts metadata from the video using yt_dlp with retries."""
        target_url = url or self.video_url
        if not target_url:
            raise ValueError("No URL provided for metadata extraction")

        logger.info("Starting metadata extraction", context={"url": target_url})

        def _extract():
            ydl_opts = self._get_common_ydl_opts()
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(target_url, download=False)
                vid = info_dict.get("id") or self.video_id or "unknown"
                return YoutubeMetadataDTO(**info_dict, video_id=vid)

        try:
            metadata = self._run_with_retry(_extract)
            logger.info(
                "Metadata successfully extracted",
                context={"video_id": metadata.video_id, "title": metadata.title},
            )
            return metadata
        except Exception as e:
            logger.error(
                "Error extracting metadata after retries",
                context={"url": target_url, "error": str(e)},
            )
            return YoutubeMetadataDTO(video_id=self.video_id or "unknown")

    def download_audio(
        self, url: str, output_dir: str = "./temp_audio", quality: str = "192"
    ) -> str | None:
        """Downloads and extracts audio from a YouTube video with resilience."""
        os.makedirs(output_dir, exist_ok=True)

        def _download():
            ydl_opts = self._get_common_ydl_opts(quiet=True)
            ydl_opts.update(
                {
                    "format": "bestaudio/best",
                    "ffmpeg_location": self._ffmpeg_path,
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": quality,
                        }
                    ],
                    "outtmpl": f"{output_dir}/%(title)s.%(ext)s",
                }
            )
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                base_name = ydl.prepare_filename(info)
                return str(Path(base_name).with_suffix(".mp3"))

        try:
            return self._run_with_retry(_download)
        except Exception as e:
            logger.error(
                f"Download failed after ALL retries: {e}", context={"url": url}
            )
            return None

    def extract_playlist_videos(self, playlist_url: str) -> list[str]:
        """Extracts all video URLs from a YouTube playlist using yt_dlp."""
        from urllib.parse import urlparse, parse_qs

        # Normalize the URL: if it contains a list=ID, use the standard playlist URL
        try:
            parsed = urlparse(playlist_url)
            query = parse_qs(parsed.query)
            if "list" in query:
                playlist_id = query["list"][0]
                playlist_url = f"https://www.youtube.com/playlist?list={playlist_id}"
                logger.info(
                    "Normalizing playlist URL",
                    context={"original": playlist_url, "normalized": playlist_url},
                )
        except Exception as e:
            logger.warning(
                "Could not normalize playlist URL",
                context={"playlist_url": playlist_url, "error": str(e)},
            )

        logger.info(
            "Starting playlist extraction", context={"playlist_url": playlist_url}
        )

        def _extract():
            ydl_opts = self._get_common_ydl_opts()
            ydl_opts.update(
                {
                    "extract_flat": True,
                    "ignore_unavailable": True,
                }
            )
            with YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                if not playlist_info or "entries" not in playlist_info:
                    return []

                # Extract original URLs or IDs from entries
                urls = []
                for entry in playlist_info["entries"]:
                    if not entry:
                        continue
                    url = entry.get("url") or entry.get("webpage_url")
                    if not url and entry.get("id"):
                        url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                    if url:
                        urls.append(url)
                return urls

        try:
            urls = self._run_with_retry(_extract)
            logger.info(
                "Playlist successfully extracted",
                context={"playlist_url": playlist_url, "count": len(urls)},
            )
            return urls
        except Exception as e:
            logger.error(
                f"Playlist extraction failed: {e}",
                context={"playlist_url": playlist_url},
            )
            return []

    def extract_transcript(self) -> FetchedTranscript:
        """Fetches the transcript for a given video with fallback support and retries."""
        if not self.video_id:
            raise ValueError("video_id is required to extract transcript")

        # Define preferred languages: requested first, then common Portuguese variants
        preferred_languages = [self.language]
        for lang in ["pt", "pt-BR", "ptbr"]:
            if lang not in preferred_languages:
                preferred_languages.append(lang)

        logger.info(
            "Starting transcript fetch.",
            context={"video_id": self.video_id, "preference": preferred_languages},
        )

        # Setup Proxy for YouTubeTranscriptApi
        proxy_config = None

        if settings.youtube.proxy_enabled:
            if settings.youtube.proxy_url:
                logger.debug(
                    "Using GenericProxyConfig for transcript fetch",
                    context={"proxy": settings.youtube.proxy_url},
                )
                proxy_config = GenericProxyConfig(
                    http_url=settings.youtube.proxy_url,
                    https_url=settings.youtube.proxy_url,
                )
            elif (
                settings.youtube.webshare_username
                and settings.youtube.webshare_username.strip()
                and settings.youtube.webshare_password
                and settings.youtube.webshare_password.strip()
            ):
                logger.debug("Using WebshareProxyConfig for transcript fetch")
                proxy_config = WebshareProxyConfig(
                    proxy_username=settings.youtube.webshare_username,
                    proxy_password=settings.youtube.webshare_password,
                )
        else:
            logger.debug("Proxy usage is disabled in settings for transcript fetch.")

        retries = 3
        last_error = None

        for attempt in range(retries):
            try:
                # Initialize API with proxy config if available
                api = YouTubeTranscriptApi(proxy_config=proxy_config)

                # First attempt: Try preferred languages in order
                transcript = api.fetch(
                    video_id=self.video_id, languages=preferred_languages
                )
                logger.debug(
                    "Transcript fetched successfully (preferred).",
                    context={
                        "video_id": self.video_id,
                        "language": preferred_languages,
                    },
                )
                return transcript

            except NoTranscriptFound:
                # Second attempt: Fallback to ANY available transcript
                try:
                    transcript_list = api.list_transcripts(self.video_id)  # type: ignore[attr-defined]
                    # Pick the first one available (this will prefer manual over generated usually)
                    fallback_transcript = next(iter(transcript_list))

                    logger.warning(
                        "Preferred languages not found. Falling back to available language",
                        context={
                            "video_id": self.video_id,
                            "preferred_languages": preferred_languages,
                            "fallback_lang": fallback_transcript.language_code,
                        },
                    )

                    return fallback_transcript.fetch()
                except Exception as e:
                    # If listing fails with network error, we might want to retry
                    if "getaddrinfo failed" in str(
                        e
                    ) or "Failed to establish a new connection" in str(e):
                        last_error = e
                        logger.warning(
                            "Network error during transcript listing. Retrying",
                            context={
                                "attempt": attempt + 1,
                                "max_retries": retries,
                                "wait_time": 2**attempt,
                                "video_id": self.video_id,
                            },
                        )
                        time.sleep(2**attempt)
                        continue

                    # If even listing fails or no transcripts at all exist
                    logger.error(
                        "No transcript available for video in ANY language",
                        context={"video_id": self.video_id, "error": str(e)},
                    )
                    raise YoutubeTranscriptNotFoundException(
                        self.video_id, self.language
                    )

            except TranscriptsDisabled:
                logger.warning(
                    "Transcripts are disabled for video",
                    context={"video_id": self.video_id},
                )
                raise YoutubeTranscriptsDisabledException(self.video_id)

            except Exception as error:
                error_msg = str(error)
                last_error = error

                if "This video is private" in error_msg:
                    raise YoutubeVideoPrivateException(self.video_id)
                if "unplayable" in error_msg.lower():
                    raise YoutubeVideoUnplayableException(
                        self.video_id, reason=error_msg
                    )

                # Connection/DNS/Proxy errors
                if (
                    "getaddrinfo failed" in error_msg
                    or "Failed to establish a new connection" in error_msg
                    or "Proxy Authentication Required" in error_msg
                    or "Tunnel connection failed" in error_msg
                ):
                    logger.warning(
                        "Network error during transcript fetch. Retrying",
                        context={
                            "attempt": attempt + 1,
                            "max_retries": retries,
                            "wait_time": 2**attempt,
                            "video_id": self.video_id,
                        },
                    )
                    time.sleep(2**attempt)
                    continue

                msg = f"Unexpected error while fetching transcript for video {self.video_id}: {error_msg}"
                logger.error(
                    error,
                    context={"video_id": self.video_id, "action": "fetch_transcript"},
                )
                raise ValueError(msg)

        # If we reached here, all retries failed due to network errors
        raise YoutubeNetworkException(self.video_id, str(last_error))
