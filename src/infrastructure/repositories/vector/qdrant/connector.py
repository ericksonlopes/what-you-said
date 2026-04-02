import warnings
from typing import Optional

from qdrant_client import QdrantClient
from src.config.logger import Logger

warnings.filterwarnings(
    "ignore", message="Api key is used with an insecure connection."
)

logger = Logger()


class QdrantConnector:
    """Wrapper for QdrantClient for lifecycle management."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        grpc_port: int = 6334,
        api_key: Optional[str] = None,
        timeout: int = 10,
    ):
        self._host = host
        self._port = port
        self._grpc_port = grpc_port
        self._api_key = api_key
        self._timeout = timeout
        self._client: Optional[QdrantClient] = None

    def __enter__(self):
        if self._client is None:
            try:
                self._client = QdrantClient(
                    host=self._host,
                    port=self._port,
                    grpc_port=self._grpc_port,
                    api_key=self._api_key,
                    timeout=self._timeout,
                    prefer_grpc=True,
                    https=False,
                    check_compatibility=False,
                )
            except Exception as e:
                logger.error(
                    "Failed to connect to Qdrant",
                    context={"host": self._host, "error": str(e)},
                )
                raise
        return self._client

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                logger.warning("Error closing Qdrant client", context={"error": str(e)})
            finally:
                self._client = None

    def is_ready(self) -> bool:
        """Check if Qdrant is live and responding."""
        try:
            with self as client:
                # Simple health check call
                client.get_collections()
                return True
        except Exception as e:
            logger.warning("Qdrant health check failed", context={"error": str(e)})
            return False
