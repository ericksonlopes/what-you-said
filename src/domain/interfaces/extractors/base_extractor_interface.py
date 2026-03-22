from abc import ABC, abstractmethod
from typing import Any, List


class IBaseExtractor(ABC):
    """Base interface for all content extractors in the system."""

    @abstractmethod
    async def extract(self, source: str, **kwargs: Any) -> List[Any]:
        """
        Extracts content from a source (URL, file path, etc.) and returns a list of LangChain Documents.

        Args:
            source: The source identifier (URL, path, etc.)
            **kwargs: Additional extraction parameters (depth, selectors, etc.)

        Returns:
            List[Any]: A list of extracted content items, typically as LangChain Documents.
        """
        pass
