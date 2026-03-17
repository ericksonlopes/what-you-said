from typing import Any, List, Optional
from uuid import UUID

from src.config.logger import Logger
from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.mappers.chunk_index_mapper import ChunkIndexMapper
from src.infrastructure.repositories.sql.chunk_index_repository import (
    ChunkIndexSQLRepository,
)


class ChunkIndexService:
    """Service that works with the chunk_index SQL table and returns domain ChunkEntity items where appropriate."""

    def __init__(
        self, repository: ChunkIndexSQLRepository, logger: Optional[Logger] = None
    ) -> None:
        self._repo = repository
        self._logger = logger or Logger()
        self._mapper = ChunkIndexMapper()

    def create_chunks(self, entities: List[ChunkEntity]) -> List[UUID]:
        rows = []
        for e in entities:
            rows.append(
                {
                    "id": e.id,
                    "content_source_id": e.content_source_id,
                    "job_id": e.job_id,
                    "chunk_id": str(e.id),
                    "content": e.content,
                    "chars": len(e.content) if e.content is not None else 0,
                    "tokens_count": e.tokens_count,
                    "language": e.language,
                    "version_number": e.version_number,
                    "vector_store_type": e.extra.get("vector_store_type") if hasattr(e, "extra") else None,
                }
            )
        return self._repo.create_chunks(rows)

    def list_by_content_source(
        self,
        content_source_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[ChunkEntity]:
        models = self._repo.list_by_content_source(
            content_source_id=content_source_id, limit=limit, offset=offset
        )
        temp = [self._mapper.model_to_entity(m) for m in models]
        return [e for e in temp if e is not None]

    def count_by_content_source(self, content_source_id: UUID) -> int:
        return self._repo.count_by_content_source(content_source_id)

    def delete_by_content_source(self, content_source_id: UUID) -> int:
        """Delete from SQL. Vector store sync should happen at Use Case level."""
        return self._repo.delete_by_content_source(content_source_id=content_source_id)

    def search(
        self, query: Optional[str], top_k: int = 10, filters: Optional[Any] = None
    ) -> List[ChunkEntity]:
        models = self._repo.search(query=query, top_k=top_k, filters=filters)
        temp = [self._mapper.model_to_entity(m) for m in models]
        return [e for e in temp if e is not None]

    def get_by_id(self, chunk_id: UUID) -> Optional[ChunkEntity]:
        """Retrieve a single chunk by its ID."""
        model = self._repo.get_by_id(chunk_id)
        if model is None:
            return None
        return self._mapper.model_to_entity(model)

    def list_chunks(
        self,
        limit: int = 100,
        offset: int = 0,
        source_id: Optional[UUID] = None,
        search_query: Optional[str] = None,
    ) -> List[ChunkEntity]:
        models = self._repo.list_chunks(
            limit=limit, offset=offset, source_id=source_id, search_query=search_query
        )
        temp = [self._mapper.model_to_entity(m) for m in models]
        return [e for e in temp if e is not None]

    def delete_chunk(self, chunk_id: UUID) -> bool:
        """Delete from SQL. Vector store sync should happen at Use Case level."""
        return self._repo.delete_chunk(chunk_id)

    def update_chunk(self, chunk_id: UUID, content: str) -> bool:
        """Update SQL. Vector store re-indexing should happen at Use Case level."""
        return self._repo.update_chunk(chunk_id, content)
