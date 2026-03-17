from typing import List, Optional, Any
from uuid import UUID

from src.config.logger import Logger
from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.interfaces.repository.retriver_repository import IVectorRepository
from src.domain.mappers.chunk_mapper import ChunkMapper
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel

logger = Logger()


class ChunkVectorService:
    """Generic service for managing and retrieving chunks in a vector store."""

    def __init__(self, repository: IVectorRepository):
        self._repository = repository
        self._mapper = ChunkMapper()

    def index_documents(self, documents: List[ChunkEntity]) -> List[str]:
        """Index a list of chunk entities into the vector store."""
        if not documents:
            logger.warning("Attempted to index empty documents list")
            return []

        logger.debug("Indexing documents", context={"count": len(documents)})
        models = [self._mapper.entity_to_model(doc) for doc in documents]
        return self._repository.create_documents(models)

    def retrieve(
        self, query: str, top_k: int = 5, filters: Optional[Any] = None
    ) -> List[ChunkEntity]:
        """Retrieve chunk entities from the vector repository based on similarity search."""
        if not query:
            raise ValueError("Query must be provided for retrieval")

        logger.debug("Retrieving chunks", context={"query": query, "top_k": top_k})
        models: List[ChunkModel] = self._repository.retriever(
            query=query, top_kn=top_k, filters=filters
        )

        entities = [self._mapper.model_to_entity(m) for m in models]

        # Ensure scores are transferred to entities if present in models
        for i, m in enumerate(models):
            if hasattr(m, "score") and i < len(entities):
                entities[i].score = m.score

        return entities

    def list_by_source(self, filters: Optional[Any] = None) -> List[ChunkEntity]:
        """List chunks associated with a specific external source using the provided filters."""
        # Note: Implementation relies on the repository's filter logic
        models = self._repository.list_chunks(filters=filters)
        return [self._mapper.model_to_entity(m) for m in models]

    def delete(self, filters: Optional[Any]) -> int:
        """Delete documents from the vector store based on provided filters."""
        logger.debug(
            "Deleting documents from vector store", context={"filters": str(filters)}
        )
        return self._repository.delete(filters=filters)

    def delete_by_id(self, chunk_id: UUID) -> int:
        """Delete a specific chunk from the vector store by its ID."""
        logger.debug(
            "Deleting specific chunk from vector store",
            context={"chunk_id": str(chunk_id)},
        )
        filters = {"id": chunk_id}
        return self._repository.delete(filters=filters)
