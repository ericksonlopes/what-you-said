from abc import ABC, abstractmethod
from typing import Any

from youtube_transcript_api import FetchedTranscript


class IYoutubeExtractor(ABC):
    """Interface for YouTube extractor service in domain layer."""

    @abstractmethod
    def extract_metadata(self) -> Any:
        """Extracts metadata from the YouTube video (domain-agnostic DTO)."""
        raise NotImplementedError

    @abstractmethod
    def extract_transcript(self) -> FetchedTranscript:
        """Fetches the transcript for a given YouTube video."""
        raise NotImplementedError
