from typing import List, Optional, Any
from uuid import UUID

from src.config.logger import Logger
from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.mappers.chunk_index_mapper import ChunkIndexMapper
from src.infrastructure.repositories.sql.chunk_index_repository import ChunkIndexSQLRepository


class ChunkIndexService:
    """Service that works with the chunk_index SQL table and returns domain ChunkEntity items where appropriate."""

    def __init__(self, repository: ChunkIndexSQLRepository, logger: Optional[Logger] = None) -> None:
        self._repo = repository
        self._logger = logger or Logger()
        self._mapper = ChunkIndexMapper()

    def create_chunks(self, entities: List[ChunkEntity]) -> List[UUID]:
        rows = []
        for e in entities:
            rows.append({
                "id": e.id,
                "content_source_id": e.content_source_id,
                "job_id": e.job_id,
                "chunk_id": str(e.id),
                "chars": len(e.content) if e.content is not None else 0,
                "language": e.language,
                "version_number": e.version_number,
            })
        return self._repo.create_chunks(rows)

    def list_by_content_source(self, content_source_id: UUID, limit: int = 1000) -> List[ChunkEntity]:
        models = self._repo.list_by_content_source(content_source_id=content_source_id, limit=limit)
        temp = [self._mapper.model_to_entity(m) for m in models]
        return [e for e in temp if e is not None]

    def delete_by_content_source(self, content_source_id: UUID) -> int:
        return self._repo.delete_by_content_source(content_source_id=content_source_id)

    def search(self, query: Optional[str], top_k: int = 10, filters: Optional[Any] = None) -> List[ChunkEntity]:
        models = self._repo.search(query=query, top_k=top_k, filters=filters)
        temp = [self._mapper.model_to_entity(m) for m in models]
        return [e for e in temp if e is not None]
