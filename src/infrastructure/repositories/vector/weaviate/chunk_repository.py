from typing import List, Optional, Any
from uuid import UUID

from weaviate.collections.classes.filters import _Filters as Filters

from src.config.logger import Logger
from src.domain.interfaces.repository.retriver_repository import IVectorRepository
from src.domain.mappers.chunk_mapper import ChunkMapper
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel
from src.infrastructure.repositories.vector.weaviate.weaviate_client import (
    WeaviateClient,
)
from src.infrastructure.repositories.vector.weaviate.weaviate_vector import (
    WeaviateVector,
)
from src.infrastructure.services.embeddding_service import EmbeddingService

logger = Logger()


class ChunkWeaviateRepository(IVectorRepository):
    def __init__(
        self,
        weaviate_client: WeaviateClient,
        embedding_service: EmbeddingService,
        collection_name: str,
        text_key: str = "content",
    ):
        self._weaviate_client: WeaviateClient = weaviate_client
        self._collection_name = collection_name
        self._embedding_service = embedding_service
        self._text_key = text_key

        self.vector_store: WeaviateVector = WeaviateVector(
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
        self, query: str, top_kn: int = 5, filters: Optional[Filters] = None
    ) -> List[ChunkModel]:
        logger.debug(
            "Retrieving with scores",
            context={"filters": filters, "query": query, "top_kn": top_kn},
        )

        try:
            with self.vector_store as vector_store:
                docs_with_scores = vector_store.similarity_search_with_score(
                    query, k=top_kn, filters=filters
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
        except Exception as e:
            logger.error(
                "Error retrieving documents", context={"query": query, "error": str(e)}
            )
            raise e

    def delete(self, filters: Optional[Filters]) -> int:
        logger.debug("Deleting documents", context={"filters": filters})
        try:
            with self._weaviate_client as client:
                collection = client.collections.get(self._collection_name)
                result = collection.data.delete_many(where=filters)

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

                response = collection.query.fetch_objects(
                    filters=filters, limit=limit, include_vector=True
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
