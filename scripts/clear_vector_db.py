import sys
import os
import shutil

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config.settings import Settings
from src.domain.entities.enums.vector_store_type_enum import VectorStoreType
from src.config.logger import Logger

logger = Logger()


def clear_vector_db():
    """Clears the vector database based on the configured store type."""
    settings = Settings()
    store_type = settings.vector.store_type

    # In this project, collection names often have dimensions appended.
    # However, for cleanup, we might want to be thorough.
    collection_name = settings.vector.collection_name_chunks

    logger.info(f"Starting Vector database cleanup (Type: {store_type})...")

    try:
        if store_type == VectorStoreType.CHROMA:
            import chromadb

            client = chromadb.HttpClient(
                host=settings.vector.chroma_host, port=settings.vector.chroma_port
            )
            collections = client.list_collections()
            for col in collections:
                # If it starts with our base name, delete it
                if col.name.startswith(collection_name):
                    logger.debug(f"Deleting Chroma collection: {col.name}")
                    client.delete_collection(col.name)
            logger.info("ChromaDB cleanup completed.")

        elif store_type == VectorStoreType.WEAVIATE:
            from src.infrastructure.repositories.vector.weaviate.weaviate_client import (
                WeaviateClient,
            )

            wv_client_wrapper = WeaviateClient(settings.vector)
            with wv_client_wrapper as client:
                collections = client.collections.list_all()
                for name in collections:
                    if name.startswith(
                        collection_name.capitalize()
                    ):  # Weaviate often capitalizes
                        logger.debug(f"Deleting Weaviate collection: {name}")
                        client.collections.delete(name)
                    elif name.lower().startswith(collection_name.lower()):
                        logger.debug(f"Deleting Weaviate collection: {name}")
                        client.collections.delete(name)
            logger.info("Weaviate cleanup completed.")

        elif store_type == VectorStoreType.FAISS:
            index_path = settings.vector.vector_index_path
            if os.path.exists(index_path):
                if os.path.isdir(index_path):
                    logger.debug(f"Removing FAISS directory: {index_path}")
                    shutil.rmtree(index_path)
                else:
                    logger.debug(f"Removing FAISS file: {index_path}")
                    os.remove(index_path)
            logger.info("FAISS cleanup completed.")

        else:
            logger.warning(
                f"Cleanup not implemented for vector store type: {store_type}"
            )

    except Exception as e:
        logger.error(f"Error during Vector database cleanup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    clear_vector_db()
