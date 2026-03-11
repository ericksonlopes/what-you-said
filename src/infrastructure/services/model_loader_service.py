import torch
from typing import Optional
from sentence_transformers import SentenceTransformer

from src.config.logger import Logger
from src.domain.interfaces.services.mode_loader_service import IModelLoaderService

logger = Logger()


class ModelLoaderService(IModelLoaderService):
    def __init__(self, model_name: str):
        super().__init__()
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_instance: Optional[SentenceTransformer] = None
        self.load_model()

    def load_model(self):
        if self.model_instance is None:
            try:
                self.model_instance = SentenceTransformer(self.model_name, device=self.device)
                logger.info("Loading model", context={"model_name": self.model_name, "device": self.device})
            except Exception as e:
                logger.error(f"Error loading model: {e}")
                raise RuntimeError(f"Failed to load model '{self.model_name}': {e}")

    @property
    def model(self) -> SentenceTransformer:
        if self.model_instance is None:
            # Attempt to (re)load the model; load_model will raise on failure.
            self.load_model()
        assert self.model_instance is not None
        return self.model_instance
