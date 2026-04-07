from abc import ABC, abstractmethod
from typing import Any, List, Optional

from src.domain.entities.enums.search_mode_enum import SearchMode
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel


class IVectorRepository(ABC):
    """Repository port for storing and retrieving domain Chunk entities."""

    @abstractmethod
    def create_documents(self, documents: List[ChunkModel]) -> List[str]:
        """Persist a list of domain Chunk entities and return created IDs."""
        raise NotImplementedError

    @abstractmethod
    def retriever(
        self,
        query: str,
        top_kn: int = 5,
        filters: Optional[Any] = None,
        search_mode: SearchMode = SearchMode.SEMANTIC,
        re_rank: bool = True,
    ) -> List[ChunkModel]:
        """Retrieve matching domain Chunk entities using the given search mode."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, filters: Optional[Any]) -> int:
        """Delete chunks matching filters and return number deleted."""
        raise NotImplementedError

    @abstractmethod
    def list_chunks(
        self, filters: Optional[Any], limit: int = 1000
    ) -> List[ChunkModel]:
        """List chunks matching query and filters without vector search."""
        raise NotImplementedError

    @abstractmethod
    def is_ready(self) -> bool:
        """Check if the vector store is ready and live."""
        raise NotImplementedError
