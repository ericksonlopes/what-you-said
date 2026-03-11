from typing import List

from langchain_core.documents import Document
from src.config.logger import Logger
from src.domain.infraestructure.repository.retriver_repository import IRetrieverRepository
from src.infrastructure.repository.weaviate.weaviate_client import WeaviateClient
from src.infrastructure.repository.weaviate.weaviate_vector import WeaviateVector
from src.infrastructure.services.embeddding_service import EmbeddingService
from weaviate.classes.query import Filter

logger = Logger()


class WeaviateYoutubeRepository(IRetrieverRepository):
    def __init__(self, weaviate_client: WeaviateClient, embedding_service: EmbeddingService, collection_name: str):
        self._weaviate_client: WeaviateClient = weaviate_client
        self._collection_name = collection_name
        self._embedding_service = embedding_service

        self.vector_store: WeaviateVector = WeaviateVector(
            client=weaviate_client,
            embedding_service=self._embedding_service,
            index_name=collection_name,
            text_key="content"
        )

    def create_documents(self, documents: List[Document]) -> List[str]:
        logger.info("Creating documents in Weaviate", context={"num_documents": len(documents)})

        try:
            texts = [doc.page_content for doc in documents]
            metadatas = [doc.metadata for doc in documents]

            with self.vector_store as vector_store:
                created_ids = vector_store.add_texts(texts=texts, metadatas=metadatas)

            logger.info("Created documents in Weaviate", context={"num_documents": len(documents),
                                                                  "created_ids_count": len(
                                                                      created_ids) if created_ids is not None else 0})
            return created_ids if created_ids is not None else []

        except Exception as e:
            logger.error("Error creating documents in Weaviate",
                         context={"num_documents": len(documents), "error": str(e)})
            return e

    def query(self, query: str, top_k: int = 5) -> List[Document]:
        logger.info("Querying Weaviate", context={"query": query})
        try:
            with self.vector_store as vector_store:
                results = vector_store.similarity_search(query, k=top_k)

                logger.info("Queried Weaviate", context={"query": query, "num_results": len(results)})
                return results
        except Exception as e:
            logger.error("Error querying Weaviate", context={"query": query, "error": str(e)})
            return e

    def delete_by_video_id(self, video_id: str) -> int:
        logger.info("Deleting documents by video ID", context={"video_id": video_id})
        try:
            with self._weaviate_client as client:
                collection = client.collections.get(self._collection_name)
                result = collection.data.delete_many(
                    where=Filter.by_property("video_id").equal(video_id)
                )

                deleted = result.matches if result is not None else 0

                logger.info("Deleted documents by video ID", context={"video_id": video_id, "deleted": deleted})
                return deleted
        except Exception as e:
            logger.error("Error deleting documents by video ID", context={"video_id": video_id, "error": str(e)})
            return e
