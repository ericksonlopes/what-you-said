from langchain_weaviate import WeaviateVectorStore

from src.config.logger import Logger
from src.infrastructure.repository.weaviate.weaviate_client import WeaviateClient
from src.infrastructure.services.embeddding_service import EmbeddingService

logger = Logger()


class WeaviateVector:
    def __init__(self,
                 client: WeaviateClient,
                 embedding_service: EmbeddingService,
                 index_name: str,
                 text_key: str):
        self._client = client
        self._embedding_service = embedding_service
        self.index_name = index_name
        self.text_key = text_key

    def __enter__(self):
        self._client = self._client.__enter__()

        return WeaviateVectorStore(
            client=self._client,
            index_name=self.index_name,
            text_key=self.text_key,
            embedding=self._embedding_service
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._client is not None:
            try:
                self._client.__exit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                logger.error(f"Error closing WeaviateConfig connection: {e}")
