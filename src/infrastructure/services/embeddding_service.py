from typing import List

from langchain_core.embeddings import Embeddings

from src.domain.interfaces.services.mode_loader_service import IModelLoaderService


class EmbeddingService(Embeddings):
    def __init__(self, model_loader_service: IModelLoaderService):
        self.model_loader_service = model_loader_service
        self.model = self.model_loader_service.model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.model.encode(t).tolist() for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self.model.encode(text).tolist()
