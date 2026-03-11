from abc import ABC, abstractmethod
from typing import List, Optional, Any

from src.infrastructure.repository.weaviate.model.chunk_model import ChunkModel


class IRetrieverRepository(ABC):
    """Repository port for storing and retrieving domain Chunk entities."""

    @abstractmethod
    def create_documents(self, documents: List[ChunkModel]) -> List[str]:
        """Persist a list of domain Chunk entities and return created IDs."""
        raise NotImplementedError

    @abstractmethod
    def retriever(self, query: str, top_kn: int = 5, filters: Optional[Any] = None) -> List[ChunkModel]:
        """Retrieve matching domain Chunk entities."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, filters: Optional[Any]) -> int:
        """Delete chunks matching filters and return number deleted."""
        raise NotImplementedError

    @abstractmethod
    def list_chunks(self, filters: Optional[Any], limit: int = 1000) -> List[ChunkModel]:
        """List chunks matching query and filters without vector search."""
        raise NotImplementedError
