from typing import Any, List, Optional, Union
from uuid import UUID

from src.application.dtos.results.search_chunks_result import SearchChunksResult
from src.config.logger import Logger
from src.domain.entities.enums.search_mode_enum import SearchMode
from src.infrastructure.services.chunk_vector_service import ChunkVectorService

logger = Logger()


class SearchUseCase:
    """Use case for semantic/BM25/hybrid search of chunks via vector service with knowledge_subject filtering.

    Can filter by subject_id (UUID or str) or by subject_name (requires ks_service).
    """

    def __init__(self, vector_service: ChunkVectorService, ks_service=None):
        self.vector_service = vector_service
        self.ks_service = ks_service

    def execute(
        self,
        query: str,
        top_k: int = 5,
        subject_ids: Optional[List[Union[str, UUID]]] = None,
        subject_name: Optional[str] = None,
        search_mode: SearchMode = SearchMode.SEMANTIC,
        re_rank: bool = True,
    ) -> SearchChunksResult:
        logger.info(
            "Executing search chunks use case",
            context={
                "query": query,
                "top_k": top_k,
                "subject_ids": [str(sid) for sid in subject_ids]
                if subject_ids
                else None,
                "subject_name": subject_name,
                "search_mode": str(search_mode),
                "re_rank": re_rank,
            },
        )

        # Validations
        if subject_ids and subject_name:
            raise ValueError("Provide only one of subject_ids or subject_name")

        filters: Optional[Any] = None
        # Resolve subject_name to ID if provided
        if subject_name:
            logger.debug(
                "Resolving subject name", context={"subject_name": subject_name}
            )
            if not self.ks_service:
                raise ValueError("ks_service is required to filter by subject_name")
            subject = self.ks_service.get_by_name(subject_name)
            if subject is None:
                logger.warning(
                    "Subject not found during search",
                    context={"subject_name": subject_name},
                )
                return SearchChunksResult(query=query, results=[], total_count=0)
            subject_ids = [subject.id]

        if subject_ids is not None:
            # filters expects a dict for metadata filtering.
            # Most vector stores support lists in metadata values.
            # We'll normalize to List[str] for downstream repositories.
            filters = {"subject_id": [str(sid) for sid in subject_ids]}

        # Execute retrieval
        logger.debug(
            "Calling vector service for retrieval",
            context={
                "query": query,
                "top_k": top_k,
                "search_mode": str(search_mode),
                "re_rank": re_rank,
            },
        )
        results = self.vector_service.retrieve(
            query,
            top_k=top_k,
            filters=filters,
            search_mode=search_mode,
            re_rank=re_rank,
        )

        # Populate subject_name in extra if ks_service is available
        if self.ks_service and results:
            subject_cache = {}
            for res in results:
                if res.subject_id and "subject_name" not in res.extra:
                    sid = str(res.subject_id)
                    if sid not in subject_cache:
                        subject = self.ks_service.get_subject_by_id(res.subject_id)
                        subject_cache[sid] = subject.name if subject else None

                    if subject_cache[sid]:
                        res.extra["subject_name"] = subject_cache[sid]

        logger.info(
            "Search completed", context={"query": query, "results_count": len(results)}
        )

        return SearchChunksResult(
            query=query,
            results=results,
            total_count=len(results),
            search_mode=search_mode.value,
        )
