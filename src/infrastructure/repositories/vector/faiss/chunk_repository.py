import json
import os
from datetime import datetime
from typing import List, Optional, Any
from uuid import UUID

from src.config.logger import Logger
from src.domain.entities.enums.search_mode_enum import SearchMode
from src.domain.interfaces.repository.retriver_repository import IVectorRepository
from src.domain.mappers.chunk_mapper import ChunkMapper
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel
from src.infrastructure.services.embedding_service import EmbeddingService

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
            logger.debug(
                "Loading existing FAISS index", context={"path": self._index_path}
            )
            try:
                self._vector_store = FAISS.load_local(
                    folder_path=self._index_path,
                    embeddings=self._embedding_service,
                    index_name=self._index_name,
                    allow_dangerous_deserialization=True,
                )
            except Exception as e:
                logger.error(
                    e, context={"action": "load_faiss_index", "path": self._index_path}
                )
                self._vector_store = None
        else:
            logger.debug(
                "FAISS index not found, it will be created upon first document addition"
            )

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
            texts: List[str] = [
                doc.content for doc in documents if doc.content is not None
            ]
            if not texts:
                return []

            # Filter documents to match texts
            valid_docs = [doc for doc in documents if doc.content is not None]
            ids = [str(doc.id) for doc in valid_docs]

            metadatas = []
            for doc in valid_docs:
                meta = doc.model_dump(
                    exclude={"content", "score"}
                )  # No longer exclude ID

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
        self,
        query: str,
        top_kn: int = 5,
        filters: Optional[Any] = None,
        search_mode: SearchMode = SearchMode.SEMANTIC,
        re_rank: bool = True,
    ) -> List[ChunkModel]:

        logger.debug(
            "Retrieving from FAISS",
            context={
                "filters": filters,
                "query": query,
                "top_kn": top_kn,
                "search_mode": str(search_mode),
                "re_rank": re_rank,
            },
        )

        if not self._vector_store:
            return []

        filter_callable = None
        if isinstance(filters, dict):

            def filter_func(metadata: dict) -> bool:
                for k, v in filters.items():
                    if str(metadata.get(k)) != str(v):
                        return False
                return True

            filter_callable = filter_func

        try:
            if search_mode == SearchMode.BM25:
                return self._bm25_search(query, top_kn, filter_callable)
            elif search_mode == SearchMode.HYBRID:
                return self._hybrid_search(query, top_kn, filter_callable)
            else:
                return self._semantic_search(query, top_kn, filter_callable)
        except Exception as e:
            logger.error(
                "Error retrieving from FAISS", context={"query": query, "error": str(e)}
            )
            raise e

    def _semantic_search(
        self, query: str, top_kn: int, filter_callable: Optional[Any]
    ) -> List[ChunkModel]:
        """Standard FAISS vector similarity search."""
        if not self._vector_store:
            return []

        docs_with_scores = self._vector_store.similarity_search_with_score(
            query, k=top_kn, filter=filter_callable
        )
        mapper = ChunkMapper()
        models: List[ChunkModel] = []
        for doc, score in docs_with_scores:
            model = mapper.document_to_model(doc)
            # FAISS returns L2 distance; convert to 0-1 similarity
            model.score = float(1.0 / (1.0 + score))
            models.append(model)
        return models

    def _get_all_docs(self, filter_callable: Optional[Any]):
        """Return all docs from docstore that pass the optional filter callable."""
        if not self._vector_store or not hasattr(self._vector_store, "docstore"):
            return []

        all_docs = list(self._vector_store.docstore._dict.values())
        if filter_callable:
            all_docs = [d for d in all_docs if filter_callable(d.metadata)]
        return all_docs

    def _bm25_search(
        self, query: str, top_kn: int, filter_callable: Optional[Any]
    ) -> List[ChunkModel]:
        """BM25 keyword search over the in-memory FAISS docstore using rank_bm25."""
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            logger.error(
                "rank_bm25 is not installed",
                context={"hint": "Run: pip install rank-bm25"},
            )
            raise ImportError(
                "rank-bm25 package required for BM25 search. Install with: pip install rank-bm25"
            )

        all_docs = self._get_all_docs(filter_callable)
        if not all_docs:
            return []

        tokenized_corpus = [
            (doc.page_content or "").lower().split() for doc in all_docs
        ]
        bm25 = BM25Okapi(tokenized_corpus)
        scores = bm25.get_scores(query.lower().split())

        # Get top_kn indices sorted by descending score
        ranked_indices = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:top_kn]

        mapper = ChunkMapper()
        models: List[ChunkModel] = []
        for idx in ranked_indices:
            if scores[idx] <= 0:
                continue
            model = mapper.document_to_model(all_docs[idx])
            model.score = float(scores[idx])
            models.append(model)
        return models

    def _hybrid_search(
        self, query: str, top_kn: int, filter_callable: Optional[Any]
    ) -> List[ChunkModel]:
        """Hybrid search: merge BM25 + semantic results using Reciprocal Rank Fusion (RRF)."""
        # Fetch more candidates per method to improve fusion quality
        fetch_k = max(top_kn * 3, 20)

        logger.debug(
            "Executing hybrid search sub-calls",
            context={"query": query, "fetch_k": fetch_k},
        )
        semantic_results = self._semantic_search(query, fetch_k, filter_callable)
        bm25_results = self._bm25_search(query, fetch_k, filter_callable)

        logger.debug(
            "Hybrid search candidates found",
            context={
                "semantic_count": len(semantic_results),
                "bm25_count": len(bm25_results),
            },
        )

        if not semantic_results and not bm25_results:
            return []

        # Build doc_id -> model map
        rrf_k = 60
        scores: dict = {}
        id_to_model: dict = {}

        def _doc_key(model: ChunkModel) -> str:
            """Ensure a deterministic string key for merging same documents from different sources."""
            # Use content hash if ID is missing or if we suspect it's unique per call
            # For FAISS, the content is the most reliable join key
            import hashlib

            try:
                content_str = (model.content or "").strip()
                content_hash = hashlib.md5(
                    content_str.encode("utf-8"), usedforsecurity=False
                ).hexdigest()
                return content_hash
            except TypeError:
                # Fallback for older python versions if needed, though 3.12+ supports it
                return hashlib.md5(content_str.encode("utf-8")).hexdigest()  # nosec B324

        for rank, model in enumerate(semantic_results):
            key = _doc_key(model)
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)
            id_to_model[key] = model

        for rank, model in enumerate(bm25_results):
            key = _doc_key(model)
            scores[key] = scores.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)
            if key not in id_to_model:
                id_to_model[key] = model

        # Sort by RRF score descending and take top_kn
        # Use a stable sort key to avoid TypeError when comparing different key types on tie-breaks
        ranked_keys = sorted(
            scores.keys(), key=lambda k: (scores[k], str(k)), reverse=True
        )[:top_kn]

        results = []
        for key in ranked_keys:
            model = id_to_model[key]
            model.score = scores[key]
            results.append(model)

        logger.info(
            "Hybrid search fusion completed", context={"total_results": len(results)}
        )
        return results

    def delete(self, filters: Optional[Any]) -> int:
        logger.debug("Deleting from FAISS", context={"filters": filters})
        if not self._vector_store:
            return 0

        try:
            if not filters:
                logger.warning(
                    "Delete called without filters in FAISS, skipping for safety."
                )
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
        logger.debug(
            "Listing chunks from FAISS", context={"filters": filters, "limit": limit}
        )

        if not self._vector_store:
            return []

        try:
            all_docs = self._vector_store.docstore._dict
            chunks: List[ChunkModel] = []
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

            # Sort by index if present
            chunks.sort(key=lambda x: x.index if x.index is not None else float("inf"))

            return chunks

        except Exception as e:
            logger.error(
                "Error listing chunks from FAISS",
                context={"filters": filters, "error": str(e)},
            )
            raise e

    def is_ready(self) -> bool:
        return self._vector_store is not None
