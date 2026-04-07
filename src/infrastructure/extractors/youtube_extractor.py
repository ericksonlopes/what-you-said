import os
import re
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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
    YoutubeIPBlockedException,
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
            "no_warnings": quiet,
            "nocheckcertificate": True,
            "quiet": True,
            # Force IPv4 to avoid "Connection refused" on some network configurations
            "source_address": "0.0.0.0",  # nosec
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
            # Use multiple clients to avoid "Sign in to confirm you're not a bot"
            # mediaconnect is often more resilient for servers
            "extractor_args": {
                "youtube": {"player_client": ["mediaconnect", "web", "mweb", "android"]}
            },
        }

        # Use cookies if provided by user in data/cookies.txt
        cookie_path = Path("data/cookies.txt")
        if cookie_path.exists():
            opts["cookiefile"] = str(cookie_path)
            logger.info(f"Using YouTube cookies from {cookie_path}")

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

                # Check for IP blockings
                if (
                    "blocking requests from your IP" in err_msg
                    or "IP is blocked" in err_msg
                ):
                    logger.error("YouTube IP Block detected in extractor retry loop")
                    raise YoutubeIPBlockedException(self.video_id or "unknown", err_msg)

                delay = initial_delay * (2**attempt)
                logger.warning(
                    f"YouTube action failed (attempt {attempt + 1}/{max_retries}). Retrying in {delay}s...",
                    context={"error": err_msg},
                )
                time.sleep(delay)
        raise last_exception

    def _get_proxy_config(self):
        """Setup Proxy for YouTubeTranscriptApi."""
        if not settings.youtube.proxy_enabled:
            logger.debug("Proxy usage is disabled in settings for transcript fetch.")
            return None

        if settings.youtube.proxy_url:
            logger.debug(
                "Using GenericProxyConfig for transcript fetch",
                context={"proxy": settings.youtube.proxy_url},
            )
            return GenericProxyConfig(
                http_url=settings.youtube.proxy_url,
                https_url=settings.youtube.proxy_url,
            )

        if (
            settings.youtube.webshare_username
            and settings.youtube.webshare_username.strip()
            and settings.youtube.webshare_password
            and settings.youtube.webshare_password.strip()
        ):
            logger.debug("Using WebshareProxyConfig for transcript fetch")
            return WebshareProxyConfig(
                proxy_username=settings.youtube.webshare_username,
                proxy_password=settings.youtube.webshare_password,
            )
        return None

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
            ydl_opts.update({"extract_flat": True, "ignore_unavailable": True})
            with YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                if not playlist_info or "entries" not in playlist_info:
                    return []

                return self._parse_playlist_entries(playlist_info["entries"])

        try:
            urls = self._run_with_retry(_extract)
            return urls
        except Exception as e:
            logger.error(
                f"Playlist extraction failed: {e}",
                context={"playlist_url": playlist_url},
            )
            return []

    def extract_channel_videos(self, channel_url: str) -> tuple[list[dict], str]:
        """Extracts all videos from a YouTube channel with metadata.

        Returns a list of dicts with keys: id, title, url, duration, thumbnail.
        Uses extract_flat to avoid downloading any video content.
        """
        logger.info(
            "Starting channel video extraction",
            context={"channel_url": channel_url},
        )

        # Normalize: ensure URL ends with /videos for complete listing
        normalized_url = channel_url.rstrip("/")
        if not normalized_url.endswith("/videos"):
            normalized_url = f"{normalized_url}/videos"

        def _extract():
            ydl_opts = self._get_common_ydl_opts()
            ydl_opts.update({"extract_flat": "in_playlist", "ignore_unavailable": True})
            with YoutubeDL(ydl_opts) as ydl:
                channel_info = ydl.extract_info(normalized_url, download=False)
                if not channel_info or "entries" not in channel_info:
                    chan = channel_info.get("channel", "") if channel_info else ""
                    return [], chan

                videos = self._parse_channel_entries(channel_info["entries"])
                channel_name = (
                    channel_info.get("channel") or channel_info.get("uploader") or ""
                )
                return videos, channel_name

        try:
            videos, channel_name = self._run_with_retry(_extract)

            logger.info(
                "Channel videos extracted successfully",
                context={
                    "channel_url": channel_url,
                    "channel_name": channel_name,
                    "count": len(videos),
                },
            )
            return videos, channel_name
        except Exception as e:
            logger.error(
                f"Channel extraction failed: {e}",
                context={"channel_url": channel_url},
            )
            raise

    def _fetch_transcript_with_fallback(
        self, api: YouTubeTranscriptApi, preferred_languages: list[str]
    ) -> FetchedTranscript:
        """Internal logic to fetch transcript with preferred languages and fallback."""
        if not self.video_id:
            raise ValueError("video_id is required to fetch transcript")

        try:
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
            transcript_list = api.list(self.video_id)
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

    def _handle_transcript_error(self, error: Exception):
        """Classify and raise specific exceptions for transcript fetch errors."""
        error_msg = str(error)

        if "This video is private" in error_msg:
            raise YoutubeVideoPrivateException(self.video_id or "unknown")
        if "unplayable" in error_msg.lower():
            raise YoutubeVideoUnplayableException(
                self.video_id or "unknown", reason=error_msg
            )

        # Hard Stop on IP Block
        if (
            "blocking requests from your IP" in error_msg
            or "IP is blocked" in error_msg
        ):
            logger.error("YouTube IP Block detected during transcript fetch")
            raise YoutubeIPBlockedException(self.video_id or "unknown", error_msg)

        if isinstance(error, TranscriptsDisabled):
            logger.warning(
                "Transcripts are disabled for video",
                context={"video_id": self.video_id},
            )
            raise YoutubeTranscriptsDisabledException(self.video_id or "unknown")

        if (
            isinstance(error, NoTranscriptFound)
            or "No transcript available" in error_msg
        ):
            logger.error(
                "No transcript available for video in ANY language",
                context={"video_id": self.video_id, "error": error_msg},
            )
            raise YoutubeTranscriptNotFoundException(
                self.video_id or "unknown", self.language
            )

        msg = f"Unexpected error while fetching transcript for video {self.video_id}: {error_msg}"
        logger.error(
            error,
            context={"video_id": self.video_id, "action": "fetch_transcript"},
        )
        raise ValueError(msg)

    def extract_transcript(self) -> FetchedTranscript:
        """Fetches the transcript for a given video with fallback support and retries."""
        if not self.video_id:
            raise ValueError("video_id is required to extract transcript")

        preferred_languages = [self.language]
        for lang in ["pt", "pt-BR", "ptbr"]:
            if lang not in preferred_languages:
                preferred_languages.append(lang)

        logger.info(
            "Starting transcript fetch.",
            context={"video_id": self.video_id, "preference": preferred_languages},
        )

        proxy_config = self._get_proxy_config()
        retries = 3
        last_error = None

        for attempt in range(retries):
            try:
                api = YouTubeTranscriptApi(proxy_config=proxy_config)
                return self._fetch_transcript_with_fallback(api, preferred_languages)

            except (NoTranscriptFound, TranscriptsDisabled) as e:
                # These are terminal for the current video logic usually, or handled by fallback
                self._handle_transcript_error(e)
            except Exception as error:
                error_msg = str(error)
                last_error = error

                # Connection/DNS/Proxy errors - Retryable
                if any(
                    x in error_msg
                    for x in [
                        "getaddrinfo failed",
                        "Failed to establish a new connection",
                        "Proxy Authentication Required",
                        "Tunnel connection failed",
                    ]
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

                self._handle_transcript_error(error)

        raise YoutubeNetworkException(self.video_id, str(last_error))

    def _parse_playlist_entries(self, entries: list) -> list[str]:
        """Extract valid URLs from playlist entries."""
        urls = []
        for entry in entries:
            if not entry:
                continue
            url = entry.get("url") or entry.get("webpage_url")
            if not url and entry.get("id"):
                url = f"https://www.youtube.com/watch?v={entry.get('id')}"
            if url:
                urls.append(url)
        return urls

    def _parse_channel_entries(self, entries: list) -> list[dict]:
        """Extract video metadata from channel entries."""
        videos = []
        for entry in entries:
            video_id = entry.get("id") if entry else None
            if not video_id:
                continue
            videos.append(
                {
                    "video_id": video_id,
                    "title": entry.get("title") or f"Video {video_id}",
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "duration": entry.get("duration"),
                    "thumbnail": (
                        entry.get("thumbnails", [{}])[-1].get("url")
                        if entry.get("thumbnails")
                        else f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                    ),
                }
            )
        return videos

    @staticmethod
    def get_video_id(url: str) -> str | None:
        """Extracts the 11-char YouTube video ID from various URL formats.

        Supports:
        - Plain 11-char ID (e.g. RM3FVX6-UA4)
        - Watch URL (e.g. youtube.com/watch?v=...)
        - Short URL (e.g. youtu.be/...)
        - Shorts URL (e.g. youtube.com/shorts/...)
        - Embed URL (e.g. youtube.com/embed/...)
        """
        if not url:
            return None

        # 1. Quick check for plain 11-char ID
        if len(url) == 11 and re.match(r"^[A-Za-z0-9_-]{11}$", url):
            return url

        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()

            # Handle youtu.be/ID
            if "youtu.be" in netloc:
                vid = parsed.path.lstrip("/")
                return vid if len(vid) == 11 else None

            # Handle youtube.com/...
            if "youtube" in netloc:
                q = parse_qs(parsed.query)
                if "v" in q:
                    vid = q["v"][0]
                    if len(vid) == 11:
                        return vid

                path_parts = [p for p in parsed.path.split("/") if p]
                # /embed/ID, /v/ID, /shorts/ID
                for i, part in enumerate(path_parts):
                    if part in ("embed", "v", "shorts") and i + 1 < len(path_parts):
                        vid = path_parts[i + 1]
                        if len(vid) == 11:
                            return vid

                # /path/ID fallback
                if path_parts:
                    potential_id = path_parts[-1]
                    if len(potential_id) == 11 and potential_id not in (
                        "videos",
                        "shorts",
                        "about",
                        "featured",
                        "playlists",
                    ):
                        return potential_id

            # 2. Broader search: look for 11-char ID preceded by common prefixes
            m = re.search(
                r"(?:v=|be/|embed/|shorts/|^|[^A-Za-z0-9_-])([A-Za-z0-9_-]{11})(?:$|[^A-Za-z0-9_-])",
                url,
            )
            if m:
                return m.group(1)

        except Exception:
            return None

        return None
