import os
import shutil
import sys
from typing import Any

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config.settings import Settings
from src.domain.entities.enums.vector_store_type_enum import VectorStoreType
from src.config.logger import Logger

logger = Logger()


def _cleanup_chroma(settings: Settings, collection_name: str):
    import chromadb
    client = chromadb.HttpClient(
        host=settings.vector.chroma_host, port=settings.vector.chroma_port
    )
    collections = client.list_collections()
    for col in collections:
        if col.name.startswith(collection_name):
            logger.debug(f"Deleting Chroma collection: {col.name}")
            client.delete_collection(col.name)
    logger.info("ChromaDB cleanup completed.")


def _cleanup_weaviate(settings: Settings, collection_name: str):
    from src.infrastructure.repositories.vector.weaviate.weaviate_client import WeaviateClient
    wv_client_wrapper = WeaviateClient(settings.vector)
    with wv_client_wrapper as client:
        collections = client.collections.list_all()
        for name in collections:
            # Weaviate often capitalizes, but we check both base and lower/upper match
            name_cap = name.capitalize()
            col_cap = collection_name.capitalize()
            if name_cap.startswith(col_cap) or name.lower().startswith(collection_name.lower()):
                logger.debug(f"Deleting Weaviate collection: {name}")
                client.collections.delete(name)
    logger.info("Weaviate cleanup completed.")


def _cleanup_qdrant(settings: Settings, collection_name: str):
    from qdrant_client import QdrantClient
    client = QdrantClient(
        host=settings.vector.qdrant_host,
        port=settings.vector.qdrant_port,
        grpc_port=settings.vector.qdrant_grpc_port,
        api_key=settings.vector.qdrant_api_key,
        prefer_grpc=True,
    )
    collections = client.get_collections().collections
    for col in collections:
        if col.name.startswith(collection_name):
            logger.debug(f"Deleting Qdrant collection: {col.name}")
            client.delete_collection(col.name)
    logger.info("Qdrant cleanup completed.")


def _cleanup_faiss(settings: Settings):
    index_path = settings.vector.vector_index_path
    if os.path.exists(index_path):
        if os.path.isdir(index_path):
            logger.debug(f"Removing FAISS directory: {index_path}")
            shutil.rmtree(index_path)
        else:
            logger.debug(f"Removing FAISS file: {index_path}")
            os.remove(index_path)
    logger.info("FAISS cleanup completed.")


def clear_vector_db():
    """Clears the vector database based on the configured store type."""
    settings = Settings()
    store_type = settings.vector.store_type
    collection_name = settings.vector.collection_name_chunks

    logger.info(f"Starting Vector database cleanup (Type: {store_type})...")

    try:
        if store_type == VectorStoreType.CHROMA:
            _cleanup_chroma(settings, collection_name)
        elif store_type == VectorStoreType.WEAVIATE:
            _cleanup_weaviate(settings, collection_name)
        elif store_type == VectorStoreType.QDRANT:
            _cleanup_qdrant(settings, collection_name)
        elif store_type == VectorStoreType.FAISS:
            _cleanup_faiss(settings)
        else:
            logger.warning(f"Cleanup not implemented for vector store type: {store_type}")

    except Exception as e:
        logger.error(f"Error during Vector database cleanup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    clear_vector_db()
