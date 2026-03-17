from enum import Enum


class VectorStoreType(Enum):
    """Enum for available vector store types."""

    CHROMA = "chroma"
    WEAVIATE = "weaviate"
    FAISS = "faiss"
