from abc import ABC, abstractmethod

from sentence_transformers import SentenceTransformer


class IModelLoaderService(ABC):
    @abstractmethod
    def load_model(self):
        """Loads the model into memory."""
        pass

    @property
    @abstractmethod
    def model(self) -> SentenceTransformer:
        """Returns the loaded model instance."""
        pass
