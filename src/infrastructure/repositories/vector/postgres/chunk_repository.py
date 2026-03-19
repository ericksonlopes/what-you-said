from typing import List, Optional, Any
from uuid import UUID

from src.config.logger import Logger
from src.domain.entities.enums.search_mode_enum import SearchMode
from src.domain.interfaces.repository.retriver_repository import IVectorRepository
from src.domain.mappers.chunk_mapper import ChunkMapper
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel
from src.infrastructure.services.embedding_service import EmbeddingService

logger = Logger()


class ChunkPostgresRepository(IVectorRepository):
    """Implementation of IVectorRepository using PostgreSQL with pgvector."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        collection_name: str,
    ):
        from src.infrastructure.repositories.vector.postgres.postgres_vector import (
            PostgresVector,
        )

        self._embedding_service = embedding_service
        self._collection_name = collection_name
        self.vector_store_ctx = PostgresVector(
            embedding_service=embedding_service,
            collection_name=collection_name,
        )

    def create_documents(self, documents: List[ChunkModel]) -> List[str]:
        logger.debug(
            "Creating documents in Postgres", context={"num_documents": len(documents)}
        )

        try:
            from langchain_core.documents import Document
            from datetime import datetime

            langchain_docs = []
            ids = []
            for doc in documents:
                # Prepare metadata for JSONB storage
                meta = doc.model_dump(exclude={"content", "id", "score"})

                # Ensure all UUID and datetime objects are strings for JSON serialization
                for key, value in meta.items():
                    if isinstance(value, UUID):
                        meta[key] = str(value)
                    elif isinstance(value, datetime):
                        meta[key] = value.isoformat()

                # 'extra' field is already a dict, but check its contents
                if "extra" in meta and isinstance(meta["extra"], dict):
                    processed_extra = {}
                    for k, v in meta["extra"].items():
                        if isinstance(v, (UUID, datetime)):
                            processed_extra[k] = str(v)
                        else:
                            processed_extra[k] = v
                    meta["extra"] = processed_extra

                langchain_docs.append(Document(page_content=doc.content or "", metadata=meta))
                ids.append(str(doc.id))

            with self.vector_store_ctx as vector_store:
                created_ids = vector_store.add_documents(
                    documents=langchain_docs, ids=ids
                )

            logger.debug(
                "Created documents in Postgres",
                context={
                    "num_documents": len(documents),
                    "created_ids_count": len(created_ids) if created_ids else 0,
                },
            )

            return [str(id_val) for id_val in created_ids]

        except Exception as e:
            logger.error(
                "Error creating documents in Postgres",
                context={"num_documents": len(documents), "error": str(e)},
            )
            raise e

    def retriever(
        self,
        query: str,
        top_kn: int = 5,
        filters: Optional[Any] = None,
        search_mode: SearchMode = SearchMode.SEMANTIC,
        re_rank: bool = True,
    ) -> List[ChunkModel]:
        # Note: Postgres search currently defaults to SEMANTIC.
        # Hybrid/BM25 would require additional setup in Postgres (tsvector).

        logger.debug(
            "Retrieving from Postgres",
            context={
                "filters": filters,
                "query": query,
                "top_kn": top_kn,
                "search_mode": str(search_mode),
            },
        )

        try:
            with self.vector_store_ctx as vector_store:
                # langchain-postgres filter format is a dict for JSONB metadata
                docs_with_scores = vector_store.similarity_search_with_score(
                    query, k=top_kn, filter=filters
                )

            mapper = ChunkMapper()
            all_models: List[ChunkModel] = []

            for doc, score in docs_with_scores:
                model = mapper.document_to_model(doc)
                model.score = score
                all_models.append(model)

            # Deduplication logic similar to Weaviate if needed
            seen = set()
            models = []
            for m in all_models:
                content_preview = (m.content or "")[:500].strip()
                source_id = str(m.external_source or "")
                key = (content_preview, source_id)

                if key not in seen:
                    seen.add(key)
                    models.append(m)

            logger.debug(
                "Retrieved documents from Postgres",
                context={
                    "query": query,
                    "total_found": len(all_models),
                    "unique_results": len(models),
                },
            )
            return models

        except Exception as e:
            logger.error(
                "Error retrieving documents from Postgres",
                context={"query": query, "error": str(e)},
            )
            raise e

    def delete(self, filters: Optional[Any]) -> int:
        if not filters:
            logger.warning(
                "Delete called without filters in Postgres, skipping for safety."
            )
            return 0

        logger.debug("Deleting documents from Postgres", context={"filters": filters})
        try:
            with self.vector_store_ctx as vector_store:
                # If filter is by ID, use standard delete
                if isinstance(filters, dict) and "id" in filters:
                    vector_store.delete(ids=[str(filters["id"])])
                    return 1

                # Generic delete by filter is not natively robust in all PostgresVectorStore versions
                # For now, we'll log and return 0. In a production scenario,
                # we'd implement a direct SQL DELETE here.
                logger.warning(
                    "Generic delete by filter not yet implemented for Postgres vector store"
                )
                return 0
        except Exception as e:
            logger.error(
                "Error deleting documents from Postgres",
                context={"filters": filters, "error": str(e)},
            )
            raise e

    def list_chunks(
        self, filters: Optional[Any], limit: int = 1000
    ) -> List[ChunkModel]:
        # list_chunks without vector search is not natively in VectorStore interface.
        # This implementation returns empty for now to satisfy interface.
        logger.warning("list_chunks not implemented for Postgres vector store")
        return []

    def is_ready(self) -> bool:
        """Check if Postgres is ready and vector extension is available."""
        try:
            self.vector_store_ctx._ensure_initialized()
            return True
        except Exception:
            return False
