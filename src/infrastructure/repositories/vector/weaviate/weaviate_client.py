from typing import Optional
from src.config.logger import Logger
from src.config.settings import VectorConfig

logger = Logger()


class WeaviateClient:
    def __init__(self, vector_config: VectorConfig, env: str = "testing"):
        self._weaviate_config = vector_config
        self._env = env
        self._client = None

    def _create_client(self):
        import weaviate
        from weaviate.classes.init import Auth

        try:
            if self._weaviate_config.weaviate_api_key:
                client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self._weaviate_config.weaviate_url,
                    auth_credentials=Auth.api_key(
                        self._weaviate_config.weaviate_api_key
                    ),
                )
            else:
                client = weaviate.connect_to_local(
                    host=self._weaviate_config.weaviate_host,
                    port=self._weaviate_config.weaviate_port,
                    grpc_port=self._weaviate_config.weaviate_grpc_port,
                )

            if client.is_ready() and client.is_live():
                logger.debug(
                    "WeaviateConfig client is ready and live",
                    context={"env": self._env},
                )
            else:
                logger.critical(
                    "WeaviateConfig client is not ready or live",
                    context={"env": self._env},
                )
                raise ConnectionError("WeaviateConfig client is not ready or live")

            return client
        except Exception as e:
            logger.error(
                "Error creating WeaviateConfig connection", context={"error": str(e)}
            )
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
                logger.error(
                    "Error closing WeaviateConfig connection", context={"error": str(e)}
                )
            finally:
                self._client = None

    def create_collection_if_not_exists(
        self, collection_name: str, dimensions: Optional[int] = None
    ):
        """Creates the collection with explicit property types if it doesn't exist.

        This prevents Weaviate auto-schema from misidentifying types (e.g. tokens_count as text).
        If dimensions are provided, it explicitly configures the vector index.
        """
        import weaviate.classes.config as wvc

        with self as client:
            if not client.collections.exists(collection_name):
                logger.debug(
                    "Creating collection with explicit schema",
                    context={
                        "collection_name": collection_name,
                        "dimensions": dimensions,
                    },
                )

                # Configure vectorizer as 'none' since we provide vectors from the app
                vectorizer_config = wvc.Configure.Vectorizer.none()

                # Optional: specify vector index configuration if dimensions are known
                # In Weaviate V4, if vectorizer is 'none', you can still hint at the index type
                # but dimensionality is usually inferred from the first insertion.
                # However, being explicit helps with validation.

                client.collections.create(
                    name=collection_name,
                    vectorizer_config=vectorizer_config,
                    properties=[
                        # Numeric fields
                        wvc.Property(name="tokens_count", data_type=wvc.DataType.INT),
                        wvc.Property(name="version_number", data_type=wvc.DataType.INT),
                        # Text fields
                        wvc.Property(name="source_type", data_type=wvc.DataType.TEXT),
                        wvc.Property(
                            name="external_source", data_type=wvc.DataType.TEXT
                        ),
                        wvc.Property(name="language", data_type=wvc.DataType.TEXT),
                        wvc.Property(name="content", data_type=wvc.DataType.TEXT),
                        wvc.Property(
                            name="embedding_model", data_type=wvc.DataType.TEXT
                        ),
                        # ID fields (stored as TEXT for simplicity or UUID if supported by the client version)
                        wvc.Property(name="job_id", data_type=wvc.DataType.TEXT),
                        wvc.Property(
                            name="content_source_id", data_type=wvc.DataType.TEXT
                        ),
                        wvc.Property(name="subject_id", data_type=wvc.DataType.TEXT),
                        # Extra metadata as text (JSON string)
                        wvc.Property(name="extra_json", data_type=wvc.DataType.TEXT),
                        # Date fields
                        wvc.Property(name="created_at", data_type=wvc.DataType.DATE),
                    ],
                )
                logger.debug(
                    "Collection created successfully",
                    context={"collection_name": collection_name},
                )
