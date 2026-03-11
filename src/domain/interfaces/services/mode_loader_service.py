from abc import ABC, abstractmethod

from sentence_transformers import SentenceTransformer


class IModelLoaderService(ABC):
    """Port for model loading and tokenizer access."""

    @abstractmethod
    def load_model(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def model(self) -> SentenceTransformer:
        raise NotImplementedError
