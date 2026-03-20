from enum import Enum


class VectorStoreType(str, Enum):
    """Available vector store types."""

    CHROMA = "chroma"
    WEAVIATE = "weaviate"
    FAISS = "faiss"
