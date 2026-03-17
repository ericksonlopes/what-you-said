from src.infrastructure.services.embedding_service import EmbeddingService
import pytest


class DummyModel:
    def encode(self, t):
        class Arr:
            def __init__(self, lst):
                self._lst = lst

            def tolist(self):
                return self._lst

        return Arr([float(len(t)), 0.5])


class DummyLoader:
    @property
    def model(self):
        return DummyModel()


@pytest.mark.EmbeddingService
class TestEmbeddingService:
    def test_embed_documents_and_query(self):
        svc = EmbeddingService(DummyLoader())
        doc_vecs = svc.embed_documents(["a", "bb"])
        assert isinstance(doc_vecs, list)
        assert all(isinstance(v, list) for v in doc_vecs)
        assert doc_vecs[0] == [1.0, 0.5]
        assert svc.embed_query("ccc") == [3.0, 0.5]
