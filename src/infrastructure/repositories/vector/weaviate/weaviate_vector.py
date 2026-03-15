from langchain_weaviate import WeaviateVectorStore

from src.config.logger import Logger
from src.infrastructure.repositories.vector.weaviate.weaviate_client import WeaviateClient

from src.infrastructure.services.embeddding_service import EmbeddingService

logger = Logger()


class WeaviateVector:
    def __init__(self,
                 client: WeaviateClient,
                 embedding_service: EmbeddingService,
                 index_name: str,
                 text_key: str,
                 use_multi_tenancy: bool = False):
        self._client_wrapper = client
        self._embedding_service = embedding_service
        self._index_name = index_name
        self._text_key = text_key
        self._use_multi_tenancy = use_multi_tenancy
        self._active_client = None

    def __enter__(self):
        """Context manager entry."""
        # Ensure collection with correct types exists using the wrapper
        self._client_wrapper.create_collection_if_not_exists(self._index_name)
        
        # Open the connection and store the low-level client
        self._active_client = self._client_wrapper.__enter__()

        return WeaviateVectorStore(
            client=self._active_client,
            index_name=self._index_name,
            text_key=self._text_key,
            embedding=self._embedding_service,
            use_multi_tenancy=self._use_multi_tenancy
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._active_client is not None:
            try:
                # Use the wrapper to close the connection
                self._client_wrapper.__exit__(exc_type, exc_val, exc_tb)
            except Exception as e:
                logger.error(f"Error closing Weaviate connection: {e}")
            finally:
                self._active_client = None
