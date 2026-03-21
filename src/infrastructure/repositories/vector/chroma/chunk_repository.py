import json
from datetime import datetime
from typing import List, Optional, Any, Dict
from uuid import UUID

from src.config.logger import Logger
from src.domain.entities.enums.search_mode_enum import SearchMode
from src.domain.interfaces.repository.retriver_repository import IVectorRepository
from src.domain.mappers.chunk_mapper import ChunkMapper
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel
from src.infrastructure.services.embedding_service import EmbeddingService

logger = Logger()


class ChunkChromaRepository(IVectorRepository):
    def __init__(
        self,
        embedding_service: EmbeddingService,
        host: str = "localhost",
        port: int = 8000,
        collection_name: str = "chunks",
    ):
        self._embedding_service = embedding_service
        self._collection_name = collection_name
        self._vector_store: Optional[Any] = None
        self._chroma_client: Optional[Any] = None

        try:
            import chromadb
            from langchain_chroma import Chroma

            # Connect to ChromaDB HTTP client
            self._chroma_client = chromadb.HttpClient(host=host, port=port)

            self._vector_store = Chroma(
                client=self._chroma_client,
                collection_name=self._collection_name,
                embedding_function=self._embedding_service,
            )
            logger.info(
                f"Connected to ChromaDB at {host}:{port}, collection: {collection_name}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            self._chroma_client = None

    def create_documents(self, documents: List[ChunkModel]) -> List[str]:
        logger.debug(
            "Creating documents in ChromaDB", context={"num_documents": len(documents)}
        )

        try:
            if not self._vector_store:
                raise ConnectionError("ChromaDB is not initialized")

            valid_docs = [doc for doc in documents if doc.content is not None]
            if not valid_docs:
                return []

            texts = [doc.content for doc in valid_docs if doc.content is not None]
            ids = [str(doc.id) for doc in valid_docs]

            meta_datas = []
            for doc in valid_docs:
                meta = doc.model_dump(exclude={"content", "score"})

                # Convert UUIDs and datetimes to string
                for key, value in meta.items():
                    if isinstance(value, UUID):
                        meta[key] = str(value)
                    elif isinstance(value, datetime):
                        meta[key] = value.isoformat()

                if "extra" in meta and isinstance(meta["extra"], dict):
                    meta["extra_json"] = json.dumps(meta.pop("extra"))

                # Clean up None values as Chroma doesn't like them in metadata
                meta = {k: v for k, v in meta.items() if v is not None}

                meta_datas.append(meta)

            self._vector_store.add_texts(
                texts=texts,
                metadatas=meta_datas,
                ids=ids,
            )

            return ids

        except Exception as e:
            logger.error(
                "Error creating documents in Chroma",
                context={"num_documents": len(documents), "error": str(e)},
            )
            raise e

    def _build_chroma_filter(self, filters: Optional[Any]) -> Optional[Dict]:
        """Convert basic dictionary filters into ChromaDB filter format."""
        if not filters or not isinstance(filters, dict):
            return None

        chroma_filters = {}
        # Simple AND logic for all provided filters
        for k, v in filters.items():
            if isinstance(v, UUID):
                v = str(v)
            chroma_filters[k] = v

        if len(chroma_filters) > 1:
            # If multiple filters, we need the $and operator
            return {"$and": [{k: {"$eq": v}} for k, v in chroma_filters.items()]}

        return chroma_filters if chroma_filters else None

    def retriever(
        self,
        query: str,
        top_kn: int = 5,
        filters: Optional[Any] = None,
        search_mode: SearchMode = SearchMode.SEMANTIC,
        re_rank: bool = True,
    ) -> List[ChunkModel]:

        logger.debug(
            "Retrieving from ChromaDB",
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

        chroma_filter = self._build_chroma_filter(filters)

        try:
            if search_mode == SearchMode.SEMANTIC:
                return self._semantic_search(query, top_kn, chroma_filter)
            elif search_mode == SearchMode.BM25:
                return self._bm25_search(query, top_kn, chroma_filter)
            elif search_mode == SearchMode.HYBRID:
                return self._hybrid_search(query, top_kn, chroma_filter)
            else:
                logger.warning(
                    f"Unknown search mode {search_mode}, falling back to SEMANTIC"
                )
                return self._semantic_search(query, top_kn, chroma_filter)

        except Exception as e:
            logger.error(
                "Error retrieving chunks from Chroma",
                context={"query": query, "error": str(e)},
            )
            return []

    def _semantic_search(
        self, query: str, top_kn: int, chroma_filter: Optional[Dict]
    ) -> List[ChunkModel]:
        """Standard Chroma vector similarity search."""
        if not self._vector_store:
            return []

        docs_with_scores = self._vector_store.similarity_search_with_score(
            query, k=top_kn, filter=chroma_filter
        )

        mapper = ChunkMapper()
        models: List[ChunkModel] = []
        for doc, score in docs_with_scores:
            model = mapper.document_to_model(doc)
            # Chroma returns L2 distance by default (lower is better)
            # Convert to similarity score (0 to 1)
            model.score = 1.0 / (1.0 + float(score))
            models.append(model)
        return models

    def _get_all_docs(self, chroma_filter: Optional[Dict]):
        """Get docs from Chroma collection for BM25. This fetches from the underlying client."""
        if not self._chroma_client:
            return []

        collection = self._chroma_client.get_collection(self._collection_name)

        # Get all documents matching the filter (or all if no filter)
        results = collection.get(
            where=chroma_filter, include=["documents", "metadatas"]
        )

        from langchain_core.documents import Document

        docs = []
        ids = results.get("ids", []) or []
        documents = results.get("documents", []) or []
        metadatas = results.get("metadatas", []) or []

        for i in range(len(ids)):
            docs.append(
                Document(
                    page_content=documents[i] if i < len(documents) else "",
                    metadata=metadatas[i] if i < len(metadatas) else {},
                )
            )
        return docs

    def _bm25_search(
        self, query: str, top_kn: int, chroma_filter: Optional[Dict]
    ) -> List[ChunkModel]:
        """BM25 keyword search over Chroma docs using rank_bm25."""
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            logger.error("rank_bm25 is not installed. Run: pip install rank-bm25")
            return []

        all_docs = self._get_all_docs(chroma_filter)
        if not all_docs:
            return []

        tokenized_corpus = [doc.page_content.lower().split() for doc in all_docs]
        bm25 = BM25Okapi(tokenized_corpus)

        tokenized_query = query.lower().split()
        scores = bm25.get_scores(tokenized_query)

        import numpy as np

        # Get top k indices
        k = min(top_kn, len(all_docs))
        if k == 0:
            return []

        top_k_indices = np.argsort(scores)[::-1][:k]

        mapper = ChunkMapper()
        models: List[ChunkModel] = []
        for idx in top_k_indices:
            if scores[idx] <= 0:
                continue
            model = mapper.document_to_model(all_docs[idx])
            model.score = float(scores[idx])
            models.append(model)

        return models

    def _hybrid_search(
        self, query: str, top_kn: int, chroma_filter: Optional[Dict]
    ) -> List[ChunkModel]:
        """Custom Hybrid search using Reciprocal Rank Fusion (RRF)."""
        fetch_k = max(top_kn * 3, 20)

        semantic_results = self._semantic_search(query, fetch_k, chroma_filter)
        bm25_results = self._bm25_search(query, fetch_k, chroma_filter)

        semantic_rank = {str(res.id): rank for rank, res in enumerate(semantic_results)}
        bm25_rank = {str(res.id): rank for rank, res in enumerate(bm25_results)}

        all_ids = set(semantic_rank.keys()) | set(bm25_rank.keys())

        # Map to find original models by ID
        model_map = {}
        for res in semantic_results + bm25_results:
            model_map[str(res.id)] = res

        # RRF Calculation
        k_c = 60
        rrf_scores = {}
        for doc_id in all_ids:
            score = 0.0
            if doc_id in semantic_rank:
                score += 1.0 / (k_c + semantic_rank[doc_id])
            if doc_id in bm25_rank:
                score += 1.0 / (k_c + bm25_rank[doc_id])
            rrf_scores[doc_id] = score

        # Sort by RRF score
        sorted_ids = sorted(
            rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True
        )

        final_results = []
        for doc_id in sorted_ids[:top_kn]:
            model = model_map[doc_id]
            model.score = rrf_scores[doc_id]
            final_results.append(model)

        logger.debug(
            "Hybrid search fusion completed",
            context={"total_results": len(final_results)},
        )
        return final_results

    def delete(self, filters: Optional[Any]) -> int:
        if not self._chroma_client:
            return 0

        logger.debug(
            "Deleting specific chunk from Chroma",
            context={"filters": filters},
        )

        try:
            chroma_filter = self._build_chroma_filter(filters)
            if not chroma_filter:
                logger.warning(
                    "Delete called without filters in Chroma, skipping for safety."
                )
                return 0

            collection = self._chroma_client.get_collection(self._collection_name)

            # Get IDs to know how many we delete
            results = collection.get(where=chroma_filter, include=[])
            ids_to_delete = results["ids"]

            if ids_to_delete:
                collection.delete(ids=ids_to_delete)

            return len(ids_to_delete)

        except Exception as e:
            logger.error(
                "Error deleting chunk from Chroma",
                context={"filters": filters, "error": str(e)},
            )
            return 0

    def list_chunks(
        self, filters: Optional[Any], limit: int = 1000
    ) -> List[ChunkModel]:
        if not self._chroma_client:
            return []

        try:
            chroma_filter = self._build_chroma_filter(filters)

            collection = self._chroma_client.get_collection(self._collection_name)
            results = collection.get(
                where=chroma_filter, limit=limit, include=["documents", "metadatas"]
            )

            mapper = ChunkMapper()
            models = []

            from langchain_core.documents import Document

            ids = results.get("ids", []) or []
            documents = results.get("documents", []) or []
            metadatas = results.get("metadatas", []) or []

            for i in range(len(ids)):
                doc = Document(
                    page_content=documents[i] if i < len(documents) else "",
                    metadata=metadatas[i] if i < len(metadatas) else {},
                )
                models.append(mapper.document_to_model(doc))

            # Sort by index if present
            models.sort(key=lambda x: x.index if x.index is not None else float("inf"))

            return models
            return models

        except Exception as e:
            logger.error(
                "Error listing chunks from Chroma",
                context={"filters": filters, "error": str(e)},
            )
            raise e

    def is_ready(self) -> bool:
        if not self._chroma_client:
            return False
        try:
            self._chroma_client.heartbeat()
            return True
        except Exception:
            return False
