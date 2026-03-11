from typing import List, Optional

from weaviate.collections.classes.filters import _Filters as Filters, Filter

from src.config.logger import Logger
from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.interfaces.repository.retriver_repository import IRetrieverRepository
from src.domain.mappers.chunk_mapper import ChunkMapper
from src.infrastructure.repository.weaviate.model.chunk_model import ChunkModel

logger = Logger()


class YouTubeService:
    def __init__(self, repository: IRetrieverRepository):
        self._repository = repository

    def index_documents(self, documents: List[ChunkEntity]) -> List[str]:
        if not documents:
            raise ValueError("No documents provided for indexing")

        mapper = ChunkMapper()

        lista_chunks = [mapper.entity_to_model(doc) for doc in documents]

        result: List[str] = self._repository.create_documents(lista_chunks)

        return result

    def search(self, query: str, top_k: int = 5, filters: Optional[Filters] = None) -> List[ChunkEntity]:
        if not query:
            raise ValueError("Query must be provided for search")

        results: List[ChunkModel] = self._repository.retriever(query=query, top_kn=top_k, filters=filters)

        mapper = ChunkMapper()
        results: List[ChunkEntity] = [mapper.model_to_entity(doc) for doc in results]

        return results

    def search_by_video_id(self, video_id: str, filters: Optional[Filters] = None) -> List[ChunkEntity]:
        if not video_id:
            raise ValueError("video_id must be provided")

        combined_filters: Filters = Filter.all_of([
            Filter.by_property("external_source").equal(video_id),
            filters if filters is not None else None
        ])

        results: List[ChunkModel] = self._repository.list_chunks(filters=combined_filters)
        mapper = ChunkMapper()

        results: List[ChunkEntity] = [mapper.model_to_entity(doc) for doc in results]

        return results

    def delete_by_video_id(self, video_id: str) -> int:
        if not video_id:
            raise ValueError("video_id must be provided")

        filters: Filters = Filter.all_of([
            Filter.by_property("external_source").equal(video_id)
        ])

        result = self._repository.delete(filters=filters)

        return result
