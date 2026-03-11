from typing import List, Optional, Any
from uuid import UUID

from langchain_core.documents import Document
from weaviate.collections.classes.filters import _Filters as Filters

from src.config.logger import Logger
from src.domain.interfaces.repository.retriver_repository import IRetrieverRepository
from src.domain.mappers.chunk_mapper import ChunkMapper
from src.infrastructure.repository.weaviate.model.chunk_model import ChunkModel
from src.infrastructure.repository.weaviate.weaviate_client import WeaviateClient
from src.infrastructure.repository.weaviate.weaviate_vector import WeaviateVector
from src.infrastructure.services.embeddding_service import EmbeddingService

logger = Logger()


class WeaviateChunkRepository(IRetrieverRepository):
    def __init__(self, weaviate_client: WeaviateClient,
                 embedding_service: EmbeddingService,
                 collection_name: str,
                 text_key: str = "content"):
        self._weaviate_client: WeaviateClient = weaviate_client
        self._collection_name = collection_name
        self._embedding_service = embedding_service
        self._text_key = text_key

        self.vector_store: WeaviateVector = WeaviateVector(
            client=weaviate_client,
            embedding_service=embedding_service,
            index_name=collection_name,
            text_key=text_key
        )

    def create_documents(self, documents: List[ChunkModel]) -> List[str]:
        logger.info("Creating documents in Weaviate", context={"num_documents": len(documents)})

        try:
            texts = [doc.content for doc in documents]
            meta_datas = [doc.model_dump(exclude={"content", "id"}) for doc in documents]
            ids = [doc.id for doc in documents]

            logger.debug("Prepared data for Weaviate", context={
                "texts": texts,
                "meta_datas": meta_datas,
                "ids": ids
            })

            if not all(isinstance(text, str) for text in texts):
                raise ValueError("All 'texts' must be strings.")
            if not all(isinstance(meta, dict) for meta in meta_datas):
                raise ValueError("All 'meta_datas' must be dictionaries.")
            if not all(isinstance(doc_id, UUID) for doc_id in ids):
                raise ValueError("All 'ids' must be strings.")

            with self.vector_store as vector_store:
                created_ids = vector_store.add_texts(texts=texts, metadatas=meta_datas, ids=ids)

            logger.info("Created documents in Weaviate", context={"num_documents": len(documents),
                                                                  "created_ids_count": len(
                                                                      created_ids) if created_ids is not None else 0})
            return created_ids if created_ids is not None else []

        except Exception as e:
            logger.error("Error creating documents in Weaviate",
                         context={"num_documents": len(documents), "error": str(e)})
            raise e

    def retriever(self, query: str, top_kn: int = 5, filters: Optional[Filters] = None) -> List[ChunkModel]:
        logger.info("Retrieving", context={
            "filters": filters,
            "query": query,
            "top_kn": top_kn
        })

        try:
            with self.vector_store as vector_store:
                retriever = vector_store.as_retriever(
                    search_kwargs={
                        "k": top_kn,
                        "filters": filters
                    }
                )
                docs: List[Document] = retriever.invoke(query)

                mapper = ChunkMapper()
                models: List[ChunkModel] = [mapper.document_to_model(doc) for doc in docs]

                logger.info("Retrieved documents", context={"query": query, "results": len(models)})
                return models
        except Exception as e:
            logger.error("Error retrieving documents", context={"query": query, "error": str(e)})
            raise e

    def delete(self, filters: Optional[Filters]) -> int:
        logger.info("Deleting documents", context={"filters": filters})
        try:
            with self._weaviate_client as client:
                collection = client.collections.get(self._collection_name)
                result = collection.data.delete_many(where=filters)

                deleted = result.matches if result is not None else 0

                logger.info("Deleted documents", context={"filters": filters, "deleted": deleted})
                return deleted
        except Exception as e:
            logger.error("Error deleting documents",
                         context={"filters": filters, "error": str(e)})
            raise e

    def list_chunks(self, filters: Optional[Any], limit: int = 1000) -> List[ChunkModel]:
        logger.info("Listing chunks", context={"filters": filters, "limit": limit})

        try:
            with self._weaviate_client as client:
                collection = client.collections.get(self._collection_name)

                logger.debug("Fetching objects with filters", context={"filters": filters, "limit": limit})

                response = collection.query.fetch_objects(
                    filters=filters,
                    limit=limit,
                    include_vector=True
                )

                chunks = []
                for obj in response.objects:
                    if not hasattr(obj, 'uuid'):
                        logger.warning("Object missing 'uuid' attribute", context={"object": obj})
                        continue

                    properties = obj.properties

                    chunk_model = ChunkModel(
                        id=UUID(str(obj.uuid)),
                        content=properties.get(self._text_key, ""),
                        **{k: v for k, v in properties.items() if k != self._text_key}
                    )
                    chunks.append(chunk_model)

                logger.info("Listed chunks", context={"filters": filters, "num_chunks": len(chunks)})
                return chunks

        except Exception as e:
            logger.error("Error listing chunks", context={"filters": filters, "error": str(e)})
            raise e
