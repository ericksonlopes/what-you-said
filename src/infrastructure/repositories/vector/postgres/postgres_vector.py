from sqlalchemy import text, create_engine
from src.config.logger import Logger
from src.config.settings import settings
from src.infrastructure.services.embedding_service import EmbeddingService

logger = Logger()


class PostgresVector:
    """Context manager and wrapper for Postgres vector storage via langchain-postgres."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        collection_name: str,
    ):
        self._embedding_service = embedding_service
        self._collection_name = collection_name
        self._connection_string = settings.sql.url
        # Convert any potential async strings to sync if needed for psycopg2
        if "postgresql+asyncpg" in self._connection_string:
            self._connection_string = self._connection_string.replace(
                "postgresql+asyncpg", "postgresql"
            )
        elif "postgresql://" not in self._connection_string:
            # Fallback/Error if not postgres
            if settings.app.env != "testing":
                logger.warning(
                    f"Connection string {self._connection_string} is not PostgreSQL. pgvector may fail."
                )

        self._initialized = False

    def _ensure_initialized(self):
        """Ensure pgvector extension is created."""
        if self._initialized:
            return

        if "postgresql" not in self._connection_string:
            return

        try:
            engine = create_engine(self._connection_string)
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
            self._initialized = True
            logger.info("Postgres vector extension ensured.")
        except Exception as e:
            logger.error(f"Error ensuring pgvector extension: {e}")
            # We don't raise here to allow it to fail later if the extension is actually missing
            # but sometimes users don't have superuser to run CREATE EXTENSION but it's already there.

    def __enter__(self):
        """Context manager entry."""
        self._ensure_initialized()

        from langchain_postgres import PostgresVectorStore

        return PostgresVectorStore(
            connection=self._connection_string,
            collection_name=self._collection_name,
            embeddings=self._embedding_service,
            use_jsonb=True,
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass
