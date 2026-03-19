from typing import List, Optional, Any, TYPE_CHECKING
from uuid import UUID

from src.config.logger import Logger
from src.domain.entities.enums.search_mode_enum import SearchMode
from src.domain.interfaces.repository.retriver_repository import IVectorRepository
from src.domain.mappers.chunk_mapper import ChunkMapper
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel

if TYPE_CHECKING:
    from src.infrastructure.repositories.vector.weaviate.weaviate_client import (
        WeaviateClient,
    )

from src.infrastructure.services.embedding_service import EmbeddingService

logger = Logger()


class ChunkWeaviateRepository(IVectorRepository):
    def __init__(
        self,
        weaviate_client: "WeaviateClient",
        embedding_service: EmbeddingService,
        collection_name: str,
        text_key: str = "content",
    ):
        from src.infrastructure.repositories.vector.weaviate.weaviate_vector import (
            WeaviateVector,
        )

        self._weaviate_client = weaviate_client
        self._collection_name = collection_name
        self._embedding_service = embedding_service
        self._text_key = text_key

        self.vector_store = WeaviateVector(
            client=weaviate_client,
            embedding_service=embedding_service,
            index_name=collection_name,
            text_key=text_key,
            use_multi_tenancy=False,
        )

    def create_documents(self, documents: List[ChunkModel]) -> List[str]:
        logger.debug(
            "Creating documents in Weaviate", context={"num_documents": len(documents)}
        )

        try:
            texts = [doc.content for doc in documents]
            ids = [doc.id for doc in documents]

            # Prepare metadata with explicit type conversions for Weaviate stability
            import json
            from datetime import datetime

            meta_datas = []
            for doc in documents:
                meta = doc.model_dump(exclude={"content", "id", "score"})

                # Convert UUIDs to strings
                for uuid_key in ["job_id", "content_source_id", "subject_id"]:
                    if meta.get(uuid_key):
                        meta[uuid_key] = str(meta[uuid_key])

                # Convert datetime to ISO string (RFC3339)
                if isinstance(meta.get("created_at"), datetime):
                    dt = meta["created_at"]
                    # If naive, assume UTC. Format with 'Z' suffix.
                    if dt.tzinfo is None:
                        meta["created_at"] = dt.isoformat() + "Z"
                    else:
                        meta["created_at"] = dt.isoformat().replace("+00:00", "Z")

                # Serialize 'extra' dict to a JSON string if it exists
                if "extra" in meta:
                    meta["extra_json"] = json.dumps(meta.pop("extra"))

                meta_datas.append(meta)

            if not all(isinstance(text, str) for text in texts):
                raise ValueError("All 'texts' must be strings.")
            if not all(isinstance(meta, dict) for meta in meta_datas):
                raise ValueError("All 'meta_datas' must be dictionaries.")
            if not all(isinstance(doc_id, UUID) for doc_id in ids):
                raise ValueError("All 'ids' must be strings.")

            with self.vector_store as vector_store:
                created_ids = vector_store.add_texts(
                    texts=texts, metadatas=meta_datas, ids=ids
                )

            logger.debug(
                "Created documents in Weaviate",
                context={
                    "num_documents": len(documents),
                    "created_ids_count": len(created_ids)
                    if created_ids is not None
                    else 0,
                },
            )

            # Ensure created_ids is a list of strings (Langchain-Weaviate might return UUID objects)
            if created_ids:
                return [str(id_val) for id_val in created_ids]

            return []

        except Exception as e:
            logger.error(
                "Error creating documents in Weaviate",
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
        # Convert dictionary filters to Weaviate filters if necessary
        from weaviate.collections.classes.filters import Filter

        weaviate_filters = filters
        if isinstance(filters, dict):
            weaviate_filters_list = []
            for k, v in filters.items():
                if k == "id":
                    weaviate_filters_list.append(Filter.by_id().equal(v))
                else:
                    weaviate_filters_list.append(Filter.by_property(k).equal(v))

            if weaviate_filters_list:
                if len(weaviate_filters_list) == 1:
                    weaviate_filters = weaviate_filters_list[0]
                else:
                    weaviate_filters = Filter.all_of(weaviate_filters_list)

        logger.debug(
            "Retrieving with scores",
            context={
                "filters": weaviate_filters,
                "query": query,
                "top_kn": top_kn,
                "search_mode": str(search_mode),
                "re_rank": re_rank,
            },
        )

        try:
            if search_mode == SearchMode.BM25:
                return self._bm25_search(query, top_kn, weaviate_filters)
            elif search_mode == SearchMode.HYBRID:
                return self._hybrid_search(query, top_kn, weaviate_filters)
            else:
                return self._semantic_search(query, top_kn, weaviate_filters)
        except Exception as e:
            logger.error(
                "Error retrieving documents", context={"query": query, "error": str(e)}
            )
            raise e

    def _semantic_search(
        self, query: str, top_kn: int, weaviate_filters: Optional[Any]
    ) -> List[ChunkModel]:
        """Standard semantic (vector) search via LangChain WeaviateVectorStore."""
        with self.vector_store as vector_store:
            docs_with_scores = vector_store.similarity_search_with_score(
                query, k=top_kn, filters=weaviate_filters
            )

            mapper = ChunkMapper()
            all_models: List[ChunkModel] = []

            for doc, score in docs_with_scores:
                model = mapper.document_to_model(doc)
                model.score = score
                all_models.append(model)

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
                "Retrieved documents with scores",
                context={
                    "query": query,
                    "total_found": len(all_models),
                    "unique_results": len(models),
                },
            )
            return models

    def _weaviate_objects_to_models(self, response_objects: list) -> List[ChunkModel]:
        """Map Weaviate query response objects to ChunkModel list."""
        chunks = []
        for obj in response_objects:
            properties = obj.properties
            chunk_model = ChunkModel(
                id=UUID(str(obj.uuid)),
                content=properties.get(self._text_key, ""),
                **{k: v for k, v in properties.items() if k != self._text_key},
            )
            # Attach score from metadata if available
            if hasattr(obj, "metadata") and obj.metadata:
                meta = obj.metadata
                if hasattr(meta, "score") and meta.score is not None:
                    chunk_model.score = float(meta.score)
                elif hasattr(meta, "distance") and meta.distance is not None:
                    # convert distance to similarity
                    chunk_model.score = float(1.0 / (1.0 + meta.distance))
            chunks.append(chunk_model)
        return chunks

    def _bm25_search(
        self, query: str, top_kn: int, weaviate_filters: Optional[Any]
    ) -> List[ChunkModel]:
        """Native Weaviate BM25 keyword search."""
        with self._weaviate_client as client:
            collection = client.collections.get(self._collection_name)
            from weaviate.classes.query import MetadataQuery

            response = collection.query.bm25(
                query=query,
                limit=top_kn,
                filters=weaviate_filters,
                return_metadata=MetadataQuery(score=True),
            )

        models = self._weaviate_objects_to_models(response.objects)
        logger.debug(
            "BM25 search completed",
            context={"query": query, "results": len(models)},
        )
        return models

    def _hybrid_search(
        self, query: str, top_kn: int, weaviate_filters: Optional[Any]
    ) -> List[ChunkModel]:
        """Native Weaviate Hybrid search (vector + BM25, alpha=0.5)."""
        # Generate query vector since Weaviate collection has no automatic vectorizer
        query_vector = self._embedding_service.embed_query(query)

        with self._weaviate_client as client:
            collection = client.collections.get(self._collection_name)
            from weaviate.classes.query import MetadataQuery

            response = collection.query.hybrid(
                query=query,
                vector=query_vector,
                limit=top_kn,
                filters=weaviate_filters,
                alpha=0.5,  # 0=pure BM25, 1=pure vector; 0.5 = equal blend
                return_metadata=MetadataQuery(score=True),
            )

        models = self._weaviate_objects_to_models(response.objects)
        logger.debug(
            "Hybrid search completed",
            context={"query": query, "results": len(models)},
        )
        return models

    def delete(self, filters: Optional[Any]) -> int:
        from weaviate.collections.classes.filters import Filter

        # Convert dictionary filters to Weaviate filters if necessary
        weaviate_filters = filters
        if isinstance(filters, dict) and filters:
            weaviate_filters_list = []
            for k, v in filters.items():
                if k == "id":
                    weaviate_filters_list.append(Filter.by_id().equal(v))
                else:
                    weaviate_filters_list.append(Filter.by_property(k).equal(v))

            if weaviate_filters_list:
                if len(weaviate_filters_list) == 1:
                    weaviate_filters = weaviate_filters_list[0]
                else:
                    weaviate_filters = Filter.all_of(weaviate_filters_list)
        elif not filters or (isinstance(filters, dict) and not filters):
            # If filters are empty, we don't want to pass a raw dict/None to delete_many
            # Weaviate v4 requires a valid Filter object for delete_many
            # To delete all, we can use a filter that matches everything (not recommended for production without care)
            # For now, let's just log and return 0 if no filter is provided to avoid accidental mass deletion
            logger.warning(
                "Delete called without filters in Weaviate, skipping for safety."
            )
            return 0

        logger.debug("Deleting documents", context={"filters": weaviate_filters})
        try:
            with self._weaviate_client as client:
                collection = client.collections.get(self._collection_name)
                result = collection.data.delete_many(where=weaviate_filters)

                deleted = result.matches if result is not None else 0

                logger.debug(
                    "Deleted documents",
                    context={"filters": filters, "deleted": deleted},
                )
                return deleted
        except Exception as e:
            logger.error(
                "Error deleting documents",
                context={"filters": filters, "error": str(e)},
            )
            raise e

    def list_chunks(
        self, filters: Optional[Any], limit: int = 1000
    ) -> List[ChunkModel]:
        logger.debug("Listing chunks", context={"filters": filters, "limit": limit})

        try:
            with self._weaviate_client as client:
                collection = client.collections.get(self._collection_name)

                logger.debug(
                    "Fetching objects with filters",
                    context={"filters": filters, "limit": limit},
                )

                # Deferred import for optional dependency
                from weaviate.collections.classes.filters import Filter

                # Convert dictionary filters to Weaviate filters if necessary
                weaviate_filters = filters
                if isinstance(filters, dict):
                    weaviate_filters_list = []
                    for k, v in filters.items():
                        if k == "id":
                            weaviate_filters_list.append(Filter.by_id().equal(v))
                        else:
                            weaviate_filters_list.append(Filter.by_property(k).equal(v))

                    if weaviate_filters_list:
                        if len(weaviate_filters_list) == 1:
                            weaviate_filters = weaviate_filters_list[0]
                        else:
                            weaviate_filters = Filter.all_of(weaviate_filters_list)

                response = collection.query.fetch_objects(
                    filters=weaviate_filters, limit=limit, include_vector=True
                )

                chunks = []
                for obj in response.objects:
                    if not hasattr(obj, "uuid"):
                        logger.warning(
                            "Object missing 'uuid' attribute", context={"object": obj}
                        )
                        continue

                    properties = obj.properties

                    chunk_model = ChunkModel(
                        id=UUID(str(obj.uuid)),
                        content=properties.get(self._text_key, ""),
                        **{k: v for k, v in properties.items() if k != self._text_key},
                    )
                    chunks.append(chunk_model)

                # Sort by index if present
                chunks.sort(
                    key=lambda x: x.index if x.index is not None else float("inf")
                )

                logger.debug(
                    "Listed chunks",
                    context={"filters": filters, "num_chunks": len(chunks)},
                )
                return chunks

        except Exception as e:
            logger.error(
                "Error listing chunks", context={"filters": filters, "error": str(e)}
            )
            raise e

    def is_ready(self) -> bool:
        with self._weaviate_client as client:
            return client.is_ready()
