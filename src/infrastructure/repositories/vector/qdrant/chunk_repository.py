from datetime import datetime
from typing import List, Optional, Any, Dict, cast, Sequence, Union
from uuid import UUID

from qdrant_client.http import models as rest

from src.config.logger import Logger
from src.domain.entities.enums.search_mode_enum import SearchMode
from src.domain.interfaces.repository.retriver_repository import IVectorRepository
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel
from src.infrastructure.repositories.vector.qdrant.connector import QdrantConnector
from src.infrastructure.services.embedding_service import EmbeddingService

logger = Logger()


class ChunkQdrantRepository(IVectorRepository):
    def __init__(
        self,
        connector: QdrantConnector,
        embedding_service: EmbeddingService,
        collection_name: str,
        text_key: str = "content",
    ):
        self._connector = connector
        self._embedding_service = embedding_service
        self._collection_name = collection_name
        self._text_key = text_key
        # Collection will be checked/created lazily on first write operation

    def _ensure_collection_exists(self):
        """Ensure the collection exists with proper configuration."""
        try:
            with self._connector as client:
                client = cast(Any, client)
                if not client.collection_exists(self._collection_name):
                    logger.info(
                        f"Creating Qdrant collection: {self._collection_name}",
                        context={"collection": self._collection_name},
                    )
                    # Get vector size from embedding service
                    vector_size = (
                        self._embedding_service.model_loader_service.dimensions
                    )

                    client.create_collection(
                        collection_name=self._collection_name,
                        vectors_config=rest.VectorParams(
                            size=vector_size,
                            distance=rest.Distance.COSINE,
                        ),
                    )

                    # Create full-text index for the content field to support BM25-like search
                    client.create_payload_index(
                        collection_name=self._collection_name,
                        field_name=self._text_key,
                        field_schema=rest.TextIndexParams(
                            type="text",
                            tokenizer=rest.TokenizerType.WORD,
                            min_token_len=2,
                            max_token_len=20,
                            lowercase=True,
                        ),
                    )
        except Exception as e:
            logger.error(
                "Error ensuring Qdrant collection exists",
                context={"collection": self._collection_name, "error": str(e)},
            )

    def create_documents(self, documents: List[ChunkModel]) -> List[str]:
        logger.debug(
            "Creating documents in Qdrant", context={"num_documents": len(documents)}
        )

        try:
            self._ensure_collection_exists()
            points = []
            for doc in documents:
                if not doc.content:
                    logger.warning(
                        "Skipping document with no content",
                        context={"doc_id": str(doc.id)},
                    )
                    continue

                # Generate embedding
                vector = self._embedding_service.embed_query(doc.content)

                # Prepare payload
                payload = doc.model_dump(exclude={"score"})

                # Convert UUIDs and datetimes for Qdrant payload
                for key, value in payload.items():
                    if isinstance(value, UUID):
                        payload[key] = str(value)
                    elif isinstance(value, datetime):
                        payload[key] = value.isoformat()

                points.append(
                    rest.PointStruct(
                        id=str(doc.id),
                        vector=vector,
                        payload=payload,
                    )
                )

            with self._connector as client:
                client = cast(Any, client)
                client.upsert(
                    collection_name=self._collection_name,
                    points=points,
                    wait=True,
                )

            return [str(doc.id) for doc in documents]

        except Exception as e:
            logger.error(
                "Error creating documents in Qdrant",
                context={"num_documents": len(documents), "error": str(e)},
            )
            raise

    def retriever(
        self,
        query: str,
        top_kn: int = 5,
        filters: Optional[Any] = None,
        search_mode: SearchMode = SearchMode.SEMANTIC,
        re_rank: bool = True,
    ) -> List[ChunkModel]:
        logger.debug(
            "Retrieving from Qdrant",
            context={
                "query": query,
                "top_kn": top_kn,
                "search_mode": str(search_mode),
                "re_rank": re_rank,
            },
        )
        self._ensure_collection_exists()

        try:
            qdrant_filters = self._convert_filters(filters)

            if search_mode == SearchMode.BM25:
                return self._bm25_search(query, top_kn, qdrant_filters)
            elif search_mode == SearchMode.HYBRID:
                return self._hybrid_search(query, top_kn, qdrant_filters)
            else:
                return self._semantic_search(query, top_kn, qdrant_filters)
        except Exception as e:
            logger.error(
                "Error retrieving from Qdrant",
                context={"query": query, "error": str(e)},
            )
            raise

    def _semantic_search(
        self, query: str, top_kn: int, filters: Optional[rest.Filter]
    ) -> List[ChunkModel]:
        query_vector = self._embedding_service.embed_query(query)

        with self._connector as client:
            client = cast(Any, client)
            search_result = client.query_points(
                collection_name=self._collection_name,
                query=query_vector,
                query_filter=filters,
                limit=top_kn,
            ).points

        return self._transform_hits(search_result)

    def _bm25_search(
        self, query: str, top_kn: int, filters: Optional[rest.Filter]
    ) -> List[ChunkModel]:
        """Qdrant full-text search as a proxy for BM25."""
        # Create a text match filter for the content
        text_filter = rest.Filter(
            must=[
                rest.FieldCondition(
                    key=self._text_key,
                    match=rest.MatchText(text=query),
                )
            ]
        )

        # Combine with existing filters
        if filters:
            if filters.must:
                # Ensure we have a list to work with
                if isinstance(text_filter.must, list):
                    current_must = text_filter.must
                elif text_filter.must is not None:
                    current_must = [text_filter.must]
                else:
                    current_must = []

                if isinstance(filters.must, list):
                    additional_must = filters.must
                else:
                    additional_must = [filters.must]

                text_filter.must = current_must + additional_must
            if filters.should:
                text_filter.should = filters.should
            if filters.must_not:
                text_filter.must_not = filters.must_not

        with self._connector as client:
            client = cast(Any, client)
            try:
                # Attempt to use the new Query API which is better for this
                search_result = client.query_points(
                    collection_name=self._collection_name,
                    query=None,  # Pure filter-based
                    prefetch=None,
                    query_filter=text_filter,
                    limit=top_kn,
                ).points
            except Exception:
                # Fallback to scroll if query_points is not available or fails
                scroll_result = client.scroll(
                    collection_name=self._collection_name,
                    scroll_filter=text_filter,
                    limit=top_kn,
                    with_payload=True,
                )[0]
                search_result = scroll_result

        return self._transform_hits(search_result)

    def _hybrid_search(
        self, query: str, top_kn: int, filters: Optional[rest.Filter]
    ) -> List[ChunkModel]:
        """Hybrid search combining semantic and text match."""
        # Simple implementation: get top results from both and merge
        semantic_results = self._semantic_search(query, top_kn * 2, filters)
        bm25_results = self._bm25_search(query, top_kn * 2, filters)

        # Merge using RRF
        return self._reciprocal_rank_fusion([semantic_results, bm25_results], top_kn)

    def _reciprocal_rank_fusion(
        self, results_lists: Sequence[Sequence[ChunkModel]], k: int = 60, top_n: int = 5
    ) -> List[ChunkModel]:
        """Merge multiple ranked lists using Reciprocal Rank Fusion."""
        fused_scores: Dict[str, float] = {}
        chunks_map: Dict[str, ChunkModel] = {}

        for results in results_lists:
            for rank, chunk in enumerate(results):
                chunk_id = str(chunk.id)
                if chunk_id not in chunks_map:
                    chunks_map[chunk_id] = chunk

                # RRF Formula: score = sum(1 / (k + rank))
                score = 1.0 / (k + rank + 1)
                fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + score

        # Sort by fused score
        sorted_ids = sorted(
            fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True
        )

        final_results = []
        for chunk_id in sorted_ids[:top_n]:
            chunk = chunks_map[chunk_id]
            chunk.score = fused_scores[chunk_id]
            final_results.append(chunk)

        return final_results

    def _convert_filters(self, filters: Optional[Any]) -> Optional[rest.Filter]:
        if filters is None:
            return None

        if isinstance(filters, rest.Filter):
            return filters

        if isinstance(filters, dict):
            must_conditions: List[
                Union[
                    rest.FieldCondition,
                    rest.IsEmptyCondition,
                    rest.IsNullCondition,
                    rest.HasIdCondition,
                    rest.HasVectorCondition,
                    rest.NestedCondition,
                    rest.Filter,
                ]
            ] = []
            for k, v in filters.items():
                if k == "id":
                    must_conditions.append(rest.HasIdCondition(has_id=[str(v)]))
                else:
                    must_conditions.append(
                        rest.FieldCondition(key=k, match=rest.MatchValue(value=v))
                    )

            if must_conditions:
                return rest.Filter(must=must_conditions)

        return None

    def _transform_hits(self, hits: List[Any]) -> List[ChunkModel]:
        chunks = []
        for hit in hits:
            payload = hit.payload
            # Extract score
            score = getattr(hit, "score", None)

            # Map payload back to ChunkModel
            # Convert string dates back to datetime objects
            if "created_at" in payload and isinstance(payload["created_at"], str):
                try:
                    payload["created_at"] = datetime.fromisoformat(
                        payload["created_at"]
                    )
                except ValueError:
                    pass

            # Convert string UUIDs back to UUID objects
            for uuid_field in ["id", "job_id", "content_source_id", "subject_id"]:
                if uuid_field in payload and isinstance(payload[uuid_field], str):
                    try:
                        payload[uuid_field] = UUID(payload[uuid_field])
                    except ValueError:
                        pass

            chunk = ChunkModel(**payload)
            chunk.score = score
            chunks.append(chunk)
        return chunks

    def delete(self, filters: Optional[Any]) -> int:
        qdrant_filters = self._convert_filters(filters)
        if not qdrant_filters:
            logger.warning(
                "Delete called without filters in Qdrant, skipping for safety."
            )
            return 0

        self._ensure_collection_exists()

        try:
            with self._connector as client:
                client = cast(Any, client)
                client.delete(
                    collection_name=self._collection_name,
                    points_selector=rest.FilterSelector(filter=qdrant_filters),
                )
                # Qdrant delete doesn't return the count of deleted points in a simple way for sync calls
                # but we return 1 as a placeholder if no error occurred
                return 1
        except Exception as e:
            logger.error("Error deleting from Qdrant", context={"error": str(e)})
            raise

    def list_chunks(
        self, filters: Optional[Any], limit: int = 1000
    ) -> List[ChunkModel]:
        qdrant_filters = self._convert_filters(filters)

        try:
            self._ensure_collection_exists()
            with self._connector as client:
                client = cast(Any, client)
                scroll_result = client.scroll(
                    collection_name=self._collection_name,
                    scroll_filter=qdrant_filters,
                    limit=limit,
                    with_payload=True,
                )[0]

            chunks = self._transform_hits(scroll_result)
            # Sort by index if present
            chunks.sort(key=lambda x: x.index if x.index is not None else float("inf"))
            return chunks
        except Exception as e:
            logger.error("Error listing chunks from Qdrant", context={"error": str(e)})
            raise

    def is_ready(self) -> bool:
        return self._connector.is_ready()
