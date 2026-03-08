from typing import List

from youtube_transcript_api import YouTubeTranscriptApi, FetchedTranscript, TranscriptsDisabled, NoTranscriptFound

from src.config.logger import Logger

logger = Logger()


class TranscriptProcessor:
    """Class to process and split YouTube transcripts."""

    @staticmethod
    def fetch_transcript(video_id: str, languages: List[str]) -> FetchedTranscript:
        """Fetches the transcript for a given video."""

        if languages is None:
            languages = ['pt']

        logger.info("Starting transcript fetch.", context={"video_id": video_id, "languages": languages})

        try:
            transcript = YouTubeTranscriptApi().fetch(video_id=video_id, languages=languages)
            logger.debug("Transcript fetched successfully.", context={"video_id": video_id,
                                                                     "languages": languages,
                                                                     "transcript_length": len(transcript)})
            return transcript

        except NoTranscriptFound as ntf:
            logger.error("Transcript not found.", context={"video_id": video_id, "languages": languages, "error": str(ntf)})
            raise

        except TranscriptsDisabled as td:
            logger.warning("Transcripts are disabled for this video.", context={"video_id": video_id, "languages": languages, "error": str(td)})
            raise

        except Exception as error:
            logger.error("Unexpected error while fetching transcript.", context={"video_id": video_id, "languages": languages, "error": str(error)})
            raise
