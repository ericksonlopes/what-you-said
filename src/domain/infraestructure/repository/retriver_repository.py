from abc import ABC, abstractmethod
from typing import List

from langchain_core.documents import Document


class IRetrieverRepository(ABC):
    @abstractmethod
    def create_documents(self, documents: List[Document]):
        ...

    @abstractmethod
    def query(self, query: str, top_k: int = 5) -> List[Document]:
        ...
