from abc import ABC, abstractmethod

from sentence_transformers import SentenceTransformer


class IModelLoaderService(ABC):
    """Port for models loading and tokenizer access."""

    @abstractmethod
    def load_model(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def model(self) -> SentenceTransformer:
        raise NotImplementedError

    @property
    @abstractmethod
    def dimensions(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def max_seq_length(self) -> int:
        raise NotImplementedError
