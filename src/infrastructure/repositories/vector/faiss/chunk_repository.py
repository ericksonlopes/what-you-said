import json
import os
from datetime import datetime
from typing import List, Optional, Any
from uuid import UUID

from src.config.logger import Logger
from src.domain.interfaces.repository.retriver_repository import IVectorRepository
from src.domain.mappers.chunk_mapper import ChunkMapper
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel
from src.infrastructure.services.embeddding_service import EmbeddingService

logger = Logger()


class ChunkFAISSRepository(IVectorRepository):
    def __init__(
            self,
            embedding_service: EmbeddingService,
            index_path: str,
            index_name: str = "index",
    ):
        self._embedding_service = embedding_service
        self._index_path = index_path
        self._index_name = index_name
        self._vector_store: Optional[Any] = None
        self._load_or_create()

    def _load_or_create(self):
        """Load the FAISS index from disk or create a new one if it doesn't exist."""
        from langchain_community.vectorstores import FAISS
        if os.path.exists(os.path.join(self._index_path, f"{self._index_name}.faiss")):
            logger.debug(f"Loading existing FAISS index from {self._index_path}")
            try:
                self._vector_store = FAISS.load_local(
                    folder_path=self._index_path,
                    embeddings=self._embedding_service,
                    index_name=self._index_name,
                    allow_dangerous_deserialization=True,
                )
            except Exception as e:
                logger.error(f"Error loading FAISS index: {e}")
                self._vector_store = None
        else:
            logger.debug("FAISS index not found, it will be created upon first document addition")

    def _save(self):
        """Save the FAISS index to disk."""
        if self._vector_store:
            os.makedirs(self._index_path, exist_ok=True)
            self._vector_store.save_local(
                folder_path=self._index_path, index_name=self._index_name
            )

    def create_documents(self, documents: List[ChunkModel]) -> List[str]:
        logger.debug(
            "Creating documents in FAISS", context={"num_documents": len(documents)}
        )

        try:
            texts = [doc.content for doc in documents]
            ids = [str(doc.id) for doc in documents]

            metadatas = []
            for doc in documents:
                meta = doc.model_dump(exclude={"content", "id", "score"})

                # Convert UUIDs and datetimes to string for better compatibility
                for key, value in meta.items():
                    if isinstance(value, UUID):
                        meta[key] = str(value)
                    elif isinstance(value, datetime):
                        meta[key] = value.isoformat()

                # Handle 'extra' field
                if "extra" in meta and isinstance(meta["extra"], dict):
                    meta["extra_json"] = json.dumps(meta.pop("extra"))

                metadatas.append(meta)

            if not self._vector_store:
                from langchain_community.vectorstores import FAISS
                self._vector_store = FAISS.from_texts(
                    texts=texts,
                    embedding=self._embedding_service,
                    metadatas=metadatas,
                    ids=ids,
                )
            else:
                self._vector_store.add_texts(
                    texts=texts,
                    metadatas=metadatas,
                    ids=ids,
                )

            self._save()
            return ids

        except Exception as e:
            logger.error(
                "Error creating documents in FAISS",
                context={"num_documents": len(documents), "error": str(e)},
            )
            raise e

    def retriever(
            self, query: str, top_kn: int = 5, filters: Optional[Any] = None
    ) -> List[ChunkModel]:
        logger.debug(
            "Retrieving from FAISS",
            context={"filters": filters, "query": query, "top_kn": top_kn},
        )

        if not self._vector_store:
            return []

        try:
            filter_callable = None
            if isinstance(filters, dict):
                def filter_func(metadata: dict) -> bool:
                    for k, v in filters.items():
                        if str(metadata.get(k)) != str(v):
                            return False
                    return True

                filter_callable = filter_func

            docs_with_scores = self._vector_store.similarity_search_with_score(
                query, k=top_kn, filter=filter_callable
            )

            mapper = ChunkMapper()
            models: List[ChunkModel] = []

            for doc, score in docs_with_scores:
                model = mapper.document_to_model(doc)
                model.score = float(score)
                models.append(model)

            return models
        except Exception as e:
            logger.error(
                "Error retrieving from FAISS",
                context={"query": query, "error": str(e)}
            )
            raise e

    def delete(self, filters: Optional[Any]) -> int:
        logger.debug("Deleting from FAISS", context={"filters": filters})
        if not self._vector_store:
            return 0

        try:

            if not filters:
                logger.warning("Delete called without filters in FAISS, skipping for safety.")
                return 0

            # If it's a simple ID filter
            if isinstance(filters, dict) and "id" in filters:
                ids_to_delete = [str(filters["id"])]
            else:
                # Find all documents matching filters
                # This is inefficient in FAISS but necessary if we want to support same interface
                all_docs = self._vector_store.docstore._dict
                ids_to_delete = []
                for doc_id, doc in all_docs.items():
                    match = True
                    if isinstance(filters, dict):
                        for k, v in filters.items():
                            if str(doc.metadata.get(k)) != str(v):
                                match = False
                                break
                    if match:
                        ids_to_delete.append(doc_id)

            if ids_to_delete:
                self._vector_store.delete(ids_to_delete)
                self._save()
                return len(ids_to_delete)
            return 0

        except Exception as e:
            logger.error(
                "Error deleting from FAISS",
                context={"filters": filters, "error": str(e)},
            )
            raise e

    def list_chunks(
            self, filters: Optional[Any], limit: int = 1000
    ) -> List[ChunkModel]:
        logger.debug("Listing chunks from FAISS", context={"filters": filters, "limit": limit})

        if not self._vector_store:
            return []

        try:
            all_docs = self._vector_store.docstore._dict
            chunks = []
            mapper = ChunkMapper()

            for doc_id, doc in all_docs.items():
                if len(chunks) >= limit:
                    break

                match = True
                if isinstance(filters, dict):
                    for k, v in filters.items():
                        if str(doc.metadata.get(k)) != str(v):
                            match = False
                            break

                if match:
                    model = mapper.document_to_model(doc)
                    chunks.append(model)

            return chunks

        except Exception as e:
            logger.error(
                "Error listing chunks from FAISS",
                context={"filters": filters, "error": str(e)}
            )
            raise e

    def is_ready(self) -> bool:
        return self._vector_store is not None
