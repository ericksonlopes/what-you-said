from youtube_transcript_api import YouTubeTranscriptApi, FetchedTranscript, TranscriptsDisabled, NoTranscriptFound
from yt_dlp import YoutubeDL

from src.config.logger import Logger
from src.domain.interfaces.extractors.youtube_extractor_interface import IYoutubeExtractor
from src.infrastructure.extractors.models.youtube_metadata_dto import YoutubeMetadataDTO

logger = Logger()


class YoutubeExtractor(IYoutubeExtractor):
    """Extracts metadata and transcripts from YouTube videos."""

    def __init__(self, video_id: str, language: str = 'pt'):
        self.video_id = video_id
        self.video_url = f"https://www.youtube.com/watch?v={video_id}"
        self.language = language

    def extract_metadata(self) -> YoutubeMetadataDTO:
        """Extracts metadata from the video using yt_dlp."""
        logger.info("Starting metadata extraction", context={"video_id": self.video_id})

        ydl_opts = {
            'logger': logger
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(self.video_url, download=False)

                metadata = YoutubeMetadataDTO(**info_dict, video_id=self.video_id)

                logger.info("Metadata successfully extracted", context={"video_id": self.video_id})
                return metadata

        except Exception as e:
            logger.error(f"Error extracting metadata for video {self.video_id}: {e}")
            return YoutubeMetadataDTO(
                video_id=self.video_id
            )

    def extract_transcript(self) -> FetchedTranscript:
        """Fetches the transcript for a given video."""
        logger.info("Starting transcript fetch.", context={"video_id": self.video_id, "language": self.language})

        try:
            transcript = YouTubeTranscriptApi().fetch(video_id=self.video_id, languages=[self.language])
            logger.debug("Transcript fetched successfully.", context={"video_id": self.video_id,
                                                                      "language": self.language,
                                                                      "transcript_length": len(transcript)})
            return transcript

        except NoTranscriptFound as ntf:
            logger.error("Transcript not found.",
                         context={"video_id": self.video_id, "language": self.language, "error": str(ntf)})
            raise

        except TranscriptsDisabled as td:
            logger.warning("Transcripts are disabled for this video.",
                           context={"video_id": self.video_id, "language": self.language, "error": str(td)})
            raise

        except Exception as error:
            logger.error("Unexpected error while fetching transcript.",
                         context={"video_id": self.video_id, "language": self.language, "error": str(error)})
            raise
