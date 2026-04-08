from typing import Any, List, Optional, Set
from uuid import UUID

from src.config.logger import Logger
from src.domain.entities.chunk_duplicate_entity import ChunkDuplicateEntity
from src.domain.entities.enums.search_mode_enum import SearchMode
from src.infrastructure.repositories.sql.chunk_duplicate_repository import (
    ChunkDuplicateSQLRepository,
)
from src.infrastructure.repositories.sql.chunk_index_repository import (
    ChunkIndexSQLRepository,
)
from src.infrastructure.services.chunk_vector_service import ChunkVectorService

logger = Logger()


class ChunkDuplicateService:
    """Service for detecting and managing duplicate chunks using vector search."""

    def __init__(
        self,
        repository: ChunkDuplicateSQLRepository,
        chunk_repo: ChunkIndexSQLRepository,
        vector_service: ChunkVectorService,
    ):
        self._repo = repository
        self._chunk_repo = chunk_repo
        self._vector_service = vector_service

    def find_and_register_duplicates(
        self, chunk_ids: List[UUID], similarity_threshold: float = 0.90
    ) -> int:
        """
        Check a list of chunks for duplicates against the entire vector store.
        If duplicates are found with similarity >= threshold, register them.
        """
        registered_count = 0
        processed_pairs: Set[tuple[str, ...]] = set()

        for cid in chunk_ids:
            chunk = self._chunk_repo.get_by_id(cid)
            if not chunk or not chunk.content:
                continue

            # Search for similar chunks
            content_str = str(chunk.content)
            similar_chunks = self._vector_service.retrieve(
                query=content_str,
                top_k=5,
                search_mode=SearchMode.SEMANTIC,
                re_rank=False,
            )

            duplicates = self._filter_duplicates(cid, similar_chunks, similarity_threshold)

            if duplicates:
                registered_count += self._register_cluster(
                    source_id=cid, 
                    source_content_source_id=str(chunk.content_source_id) if chunk.content_source_id else None,
                    duplicates=duplicates, 
                    processed_pairs=processed_pairs
                )

        return registered_count

    def _filter_duplicates(self, source_id: UUID, similar_chunks: List[Any], threshold: float) -> List[tuple[UUID, float]]:
        """Filter results to find valid duplicates above threshold."""
        duplicates = []
        source_id_str = str(source_id)
        for sim_chunk in similar_chunks:
            if str(sim_chunk.id) == source_id_str:
                continue
            
            score = getattr(sim_chunk, "score", 0.0)
            if score >= threshold:
                duplicates.append((sim_chunk.id, float(score)))
        return duplicates

    def _register_cluster(
        self,
        source_id: UUID,
        source_content_source_id: Optional[str],
        duplicates: List[tuple[UUID, float]],
        processed_pairs: Set[tuple[str, ...]]
    ) -> int:
        """Register a new duplicate group if not already processed."""
        duplicate_ids = [d[0] for d in duplicates]
        all_uuids = [source_id] + duplicate_ids
        # Sort as strings for consistent cluster identification
        cluster_ids_str = sorted([str(cid) for cid in all_uuids])
        cluster_key = tuple(cluster_ids_str)

        if cluster_key not in processed_pairs:
            # Get exact similarity for the highest match
            max_sim = max([float(d[1]) for d in duplicates] + [0.0])
            self._repo.create_duplicate_record(
                chunk_ids=all_uuids,
                similarity=max_sim,
                status="pending",
                content_source_id=source_content_source_id
            )
            processed_pairs.add(cluster_key)
            return 1
        return 0

    def list_duplicates(
        self,
        status: Optional[str] = None,
        subject_ids: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[ChunkDuplicateEntity], int]:
        """List mapped duplicate records."""
        models, total = self._repo.list_duplicates(status=status, subject_ids=subject_ids, limit=limit, offset=offset)
        entities = []
        from datetime import datetime
        for m in models:
            chunk_ids: List[UUID] = []
            if isinstance(m.chunk_ids, list):
                for cid in m.chunk_ids:
                    if isinstance(cid, str):
                        chunk_ids.append(UUID(cid))
                    elif isinstance(cid, UUID):
                        chunk_ids.append(cid)
            
            # Ensure datetime types for Mypy
            created_at = m.created_at if isinstance(m.created_at, datetime) else datetime.now()
            updated_at = m.updated_at if isinstance(m.updated_at, datetime) else datetime.now()

            entities.append(ChunkDuplicateEntity(
                id=UUID(str(m.id)),
                chunk_ids=chunk_ids,
                similarity=float(m.similarity),
                content_source_id=str(m.content_source_id) if m.content_source_id else None,
                status=str(m.status),
                created_at=created_at,
                updated_at=updated_at,
            ))
        return entities, total

    def resolve_duplicate(self, duplicate_id: UUID, status: str) -> bool:
        """Mark a duplicate record as resolved (ignored, reviewed, etc)."""
        return self._repo.update_status(duplicate_id, status)

    def deactivate_chunk(self, chunk_id: UUID) -> bool:
        """
        Deactivate a chunk in both SQL and Vector Store.
        """
        # 1. Update SQL status to inactive
        success = self._chunk_repo.update_is_active(chunk_id, False)
        if success:
            # 2. Remove from Vector Store to stop it from appearing in RAG
            self._vector_service.delete_by_id(chunk_id)
            return True
        return False
