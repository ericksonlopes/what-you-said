import uuid
from types import SimpleNamespace

from src.application.use_cases.search_chunks_use_case import SearchChunksUseCase


class DummyVectorService:
    def __init__(self):
        self.last_query = None
        self.last_top_k = None
        self.last_filters = None

    def retrieve(self, query: str, top_k: int = 5, filters=None):
        self.last_query = query
        self.last_top_k = top_k
        self.last_filters = filters
        # return dummy chunks as simple objects (avoid ChunkEntity validation in tests)
        return [SimpleNamespace(id=uuid.uuid4(), content="a", subject_id=uuid.uuid4())]


class DummyKS:
    def get_by_name(self, name: str):
        return SimpleNamespace(id=uuid.uuid4(), name=name)


def test_search_filters_by_subject_id():
    vec = DummyVectorService()
    uc = SearchChunksUseCase(vector_service=vec, ks_service=None)

    uc.execute(query="hello", top_k=3, subject_id=uuid.uuid4())

    assert vec.last_query == "hello"
    assert vec.last_top_k == 3
    assert vec.last_filters is not None


def test_search_resolves_subject_name(monkeypatch):
    vec = DummyVectorService()
    ks = DummyKS()
    uc = SearchChunksUseCase(vector_service=vec, ks_service=ks)

    uc.execute(query="hello", top_k=2, subject_name="Alice")

    assert vec.last_query == "hello"
    assert vec.last_top_k == 2
    assert vec.last_filters is not None
