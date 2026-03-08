from youtube_transcript_api import YouTubeTranscriptApi, FetchedTranscript, TranscriptsDisabled, NoTranscriptFound

from src.config.logger import Logger

logger = Logger()


class YoutubeTranscriptExtractor:
    """Class to process and split YouTube transcripts."""

    @staticmethod
    def fetch_transcript(video_id: str, language: str = 'pt') -> FetchedTranscript:
        """Fetches the transcript for a given video."""

        logger.info("Starting transcript fetch.", context={"video_id": video_id, "language": language})

        try:
            transcript = YouTubeTranscriptApi().fetch(video_id=video_id, languages=[language])
            logger.debug("Transcript fetched successfully.", context={"video_id": video_id,
                                                                      "language": language,
                                                                      "transcript_length": len(transcript)})
            return transcript

        except NoTranscriptFound as ntf:
            logger.error("Transcript not found.",
                         context={"video_id": video_id, "language": language, "error": str(ntf)})
            raise

        except TranscriptsDisabled as td:
            logger.warning("Transcripts are disabled for this video.",
                           context={"video_id": video_id, "language": language, "error": str(td)})
            raise

        except Exception as error:
            logger.error("Unexpected error while fetching transcript.",
                         context={"video_id": video_id, "language": language, "error": str(error)})
            raise
