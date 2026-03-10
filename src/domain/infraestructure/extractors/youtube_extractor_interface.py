from abc import ABC, abstractmethod

from youtube_transcript_api import FetchedTranscript

from src.infrastructure.extractors.models.youtube_metadata_dto import YoutubeMetadataDTO


class IYoutubeExtractor(ABC):
    """Interface for YouTube extractor service."""

    @abstractmethod
    def extract_metadata(self) -> YoutubeMetadataDTO:
        """Extracts metadata from the YouTube video."""
        pass

    @abstractmethod
    def extract_transcript(self) -> FetchedTranscript:
        """Fetches the transcript for a given YouTube video and language."""
        pass
