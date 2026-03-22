import time
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    FetchedTranscript,
    TranscriptsDisabled,
    NoTranscriptFound,
)
from yt_dlp import YoutubeDL

from src.config.logger import Logger
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
    """Extracts metadata and transcripts from YouTube videos."""

    def __init__(self, video_id: str, language: str = "pt"):
        self.video_id = video_id
        self.video_url = f"https://www.youtube.com/watch?v={video_id}"
        self.language = language

    def extract_metadata(self) -> YoutubeMetadataDTO:
        """Extracts metadata from the video using yt_dlp."""
        logger.info("Starting metadata extraction", context={"video_id": self.video_id})

        ydl_opts = {"logger": logger}

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(self.video_url, download=False)

                metadata = YoutubeMetadataDTO(**info_dict, video_id=self.video_id)

                logger.info(
                    "Metadata successfully extracted",
                    context={"video_id": self.video_id, "title": metadata.title},
                )
                return metadata

        except Exception as e:
            error_msg = str(e)
            if "This video is private" in error_msg:
                raise YoutubeVideoPrivateException(self.video_id)
            if "unplayable" in error_msg.lower():
                raise YoutubeVideoUnplayableException(self.video_id, reason=error_msg)
            if (
                "getaddrinfo failed" in error_msg
                or "Failed to establish a new connection" in error_msg
            ):
                raise YoutubeNetworkException(self.video_id, error_msg)

            logger.error(
                "Error extracting metadata for video",
                context={"video_id": self.video_id, "error": error_msg},
            )
            return YoutubeMetadataDTO(video_id=self.video_id)

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
            logger.warning(f"Could not normalize playlist URL: {e}")

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
            logger.error(f"Error extracting playlist {playlist_url}: {e}")
            return []

    def extract_transcript(self) -> FetchedTranscript:
        """Fetches the transcript for a given video with fallback support and retries."""
        # Define preferred languages: requested first, then common Portuguese variants
        preferred_languages = [self.language]
        for lang in ["pt", "pt-BR", "ptbr"]:
            if lang not in preferred_languages:
                preferred_languages.append(lang)

        logger.info(
            "Starting transcript fetch.",
            context={"video_id": self.video_id, "preference": preferred_languages},
        )

        retries = 3
        last_error = None

        for attempt in range(retries):
            try:
                # First attempt: Try preferred languages in order
                transcript = YouTubeTranscriptApi().fetch(
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
                    transcript_list = YouTubeTranscriptApi().list(self.video_id)
                    # Pick the first one available (this will prefer manual over generated usually)
                    fallback_transcript = next(iter(transcript_list))

                    logger.warning(
                        f"Preferred languages {preferred_languages} not found. "
                        f"Falling back to available language: '{fallback_transcript.language_code}'",
                        context={
                            "video_id": self.video_id,
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
                            f"Network error during transcript listing (attempt {attempt + 1}/{retries}). Retrying in {2**attempt}s..."
                        )
                        time.sleep(2**attempt)
                        continue

                    # If even listing fails or no transcripts at all exist
                    msg = f"No transcript available for video {self.video_id} in ANY language."
                    logger.error(
                        msg, context={"video_id": self.video_id, "error": str(e)}
                    )
                    raise YoutubeTranscriptNotFoundException(
                        self.video_id, self.language
                    )

            except TranscriptsDisabled:
                msg = f"Transcripts are disabled for video {self.video_id}."
                logger.warning(msg, context={"video_id": self.video_id})
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

                # Connection/DNS errors
                if (
                    "getaddrinfo failed" in error_msg
                    or "Failed to establish a new connection" in error_msg
                ):
                    logger.warning(
                        f"Network error during transcript fetch (attempt {attempt + 1}/{retries}). Retrying in {2**attempt}s..."
                    )
                    time.sleep(2**attempt)
                    continue

                msg = f"Unexpected error while fetching transcript for video {self.video_id}: {error_msg}"
                logger.error(msg, context={"video_id": self.video_id})
                raise ValueError(msg)

        # If we reached here, all retries failed due to network errors
        raise YoutubeNetworkException(self.video_id, str(last_error))
