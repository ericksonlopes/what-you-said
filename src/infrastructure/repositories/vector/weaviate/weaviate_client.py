import weaviate
from src.config.logger import Logger
from src.config.settings import VectorConfig
from weaviate.classes.init import Auth

logger = Logger()


class WeaviateClient:
    def __init__(self, vector_config: VectorConfig, env: str = "testing"):
        self._weaviate_config = vector_config
        self._env = env
        self._client = None

    def _create_client(self):
        try:
            if self._env == "testing":
                logger.debug("Creating WeaviateConfig client", context={"env": self._env})
                client = weaviate.connect_to_local(
                    host=self._weaviate_config.weaviate_host,
                    port=self._weaviate_config.weaviate_port,
                    grpc_port=self._weaviate_config.weaviate_grpc_port,
                )
            else:
                client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self._weaviate_config.weaviate_url,
                    auth_credentials=Auth.api_key(self._weaviate_config.weaviate_api_key),
                )

            if client.is_ready() and client.is_live():
                logger.debug("WeaviateConfig client is ready and live", context={"env": self._env})
            else:
                logger.critical("WeaviateConfig client is not ready or live", context={"env": self._env})
                raise ConnectionError("WeaviateConfig client is not ready or live")

            return client
        except Exception as e:
            logger.error("Error creating WeaviateConfig connection", context={"error": str(e)})
            raise

    def __enter__(self):
        """Context manager entry."""
        self._client = self._create_client()
        return self._client

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception as e:
                logger.error("Error closing WeaviateConfig connection", context={"error": str(e)})
            finally:
                self._client = None
