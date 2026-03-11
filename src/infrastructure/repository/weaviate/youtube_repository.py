from typing import List

from langchain_core.documents import Document

from src.config.logger import Logger
from src.domain.infraestructure.repository.retriver_repository import IRetrieverRepository
from src.infrastructure.repository.weaviate.weaviate_client import WeaviateClient

logger = Logger()


class WeaviateYoutubeRepository(IRetrieverRepository):
    def __init__(self, weaviate_vector: WeaviateClient):
        self.weaviate_client = weaviate_vector

    def create_documents(self, documents: List[Document]):
        logger.info("Creating documents in Weaviate", context={"num_documents": len(documents)})

        with self.weaviate_client as vector_store:
            for doc in documents:
                vector_store.add_texts(texts=[doc.page_content], metadatas=[doc.metadata])

    def query(self, query: str, top_k: int = 5) -> List[Document]:
        logger.info("Querying Weaviate", context={"query": query})
        with self.weaviate_client as vector_store:
            results = vector_store.similarity_search(query, k=top_k)
            return results
