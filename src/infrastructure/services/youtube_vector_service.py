from typing import Any, List, Optional

from src.config.logger import Logger
from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.interfaces.repository.retriver_repository import IVectorRepository
from src.domain.mappers.chunk_mapper import ChunkMapper
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel

logger = Logger()


class YouTubeVectorService:
    def __init__(self, repository: IVectorRepository):
        self._repository = repository

    def index_documents(self, documents: List[ChunkEntity]) -> List[str]:
        if not documents:
            raise ValueError("No documents provided for indexing")

        mapper = ChunkMapper()

        lista_chunks = [mapper.entity_to_model(doc) for doc in documents]

        result: List[str] = self._repository.create_documents(lista_chunks)

        return result

    def search(self, query: str, top_k: int = 5, filters: Optional[Any] = None) -> List[ChunkEntity]:
        if not query:
            raise ValueError("Query must be provided for search")

        models: List[ChunkModel] = self._repository.retriever(query=query, top_kn=top_k, filters=filters)

        mapper = ChunkMapper()
        entities: List[ChunkEntity] = [mapper.model_to_entity(doc) for doc in models]

        return entities

    def search_by_video_id(self, video_id: str, filters: Optional[Any] = None) -> List[ChunkEntity]:
        if not video_id:
            raise ValueError("video_id must be provided")

        combined_filters = {"external_source": video_id}
        if filters:
            if isinstance(filters, dict):
                combined_filters.update(filters)
            else:
                # If it's already a specialized filter object from another repo,
                # we just pass it through, but we prefer dicts now.
                combined_filters = filters

        models: List[ChunkModel] = self._repository.list_chunks(filters=combined_filters)
        mapper = ChunkMapper()

        entities: List[ChunkEntity] = [mapper.model_to_entity(doc) for doc in models]

        return entities

    def delete_by_video_id(self, video_id: str) -> int:
        if not video_id:
            raise ValueError("video_id must be provided")

        filters = {"external_source": video_id}

        result = self._repository.delete(filters=filters)

        return result

    def delete_by_job_id(self, job_id: Any) -> int:
        """Delete all chunks from vector store associated with a specific job_id."""
        if not job_id:
            return 0

        # Most vector stores expect string IDs
        filters = {"job_id": str(job_id)}
        result = self._repository.delete(filters=filters)

        return result
