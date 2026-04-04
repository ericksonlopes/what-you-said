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

    def extract_metadata(self, url: str | None = None) -> YoutubeMetadataDTO:
        """Extracts metadata from the video using yt_dlp."""
        target_url = url or self.video_url
        if not target_url:
            raise ValueError("No URL provided for metadata extraction")

        logger.info("Starting metadata extraction", context={"url": target_url})

        ydl_opts: dict = {"logger": logger, "quiet": True, "no_warnings": True}

        # Handle Proxy for yt-dlp
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
                ydl_opts["proxy"] = proxy

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(target_url, download=False)
                vid = info_dict.get("id") or self.video_id or "unknown"
                metadata = YoutubeMetadataDTO(**info_dict, video_id=vid)

                logger.info(
                    "Metadata successfully extracted",
                    context={"video_id": vid, "title": metadata.title},
                )
                return metadata

        except Exception as e:
            error_msg = str(e)
            logger.error(
                "Error extracting metadata",
                context={"url": target_url, "error": error_msg},
            )
            return YoutubeMetadataDTO(video_id=self.video_id or "unknown")

    def download_audio(
        self, url: str, output_dir: str = "./temp_audio", quality: str = "192"
    ) -> str | None:
        """Downloads and extracts audio from a YouTube video."""
        os.makedirs(output_dir, exist_ok=True)
        ydl_opts = {
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
            "quiet": True,
            "no_warnings": True,
            "logger": logger,
        }

        # Proxy for download
        if settings.youtube.proxy_enabled and settings.youtube.proxy_url:
            ydl_opts["proxy"] = settings.youtube.proxy_url

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                base_name = ydl.prepare_filename(info)
                final_path = str(Path(base_name).with_suffix(".mp3"))
                return final_path
        except Exception as e:
            logger.error(f"Download failed: {e}", context={"url": url})
            return None

    @staticmethod
    def extract_playlist_videos(playlist_url: str) -> list[str]:
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
        ydl_opts = {
            "extract_flat": True,
            "quiet": True,
            "no_warnings": True,
            "ignore_unavailable": True,
            "logger": logger,
        }
        try:
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

                logger.info(
                    "Playlist successfully extracted",
                    context={"playlist_url": playlist_url, "count": len(urls)},
                )
                return urls
        except Exception as e:
            logger.error(e, context={"playlist_url": playlist_url})
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
