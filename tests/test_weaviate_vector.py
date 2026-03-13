from types import SimpleNamespace
import pytest

from src.infrastructure.repositories.vector.weaviate.weaviate_vector import WeaviateVector


class DummyClientContext:
    def __init__(self):
        self.entered = False
        self.exited_args = None

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, tb):
        self.exited_args = (exc_type, exc, tb)


class DummyEmbedding:
    pass


@pytest.mark.WeaviateVector
class TestWeaviateVector:
    def test_enter_returns_weaviate_vector_store(self, monkeypatch):
        captured = {}

        class FakeWeaviateVectorStore:
            def __init__(self, client, index_name, text_key, embedding, use_multi_tenancy):
                captured['client'] = client
                captured['index_name'] = index_name
                captured['text_key'] = text_key
                captured['embedding'] = embedding
                captured['use_multi_tenancy'] = use_multi_tenancy

            def as_retriever(self, search_kwargs):
                return SimpleNamespace(invoke=lambda q: [])

        monkeypatch.setattr(
            'src.infrastructure.repositories.vector.weaviate.weaviate_vector.WeaviateVectorStore',
            FakeWeaviateVectorStore,
        )

        client_ctx = DummyClientContext()
        ev = WeaviateVector(
            client=client_ctx, embedding_service=DummyEmbedding(), index_name='idx', text_key='text',
            use_multi_tenancy=False
        )

        with ev:
            # ensure FakeWeaviateVectorStore was constructed with the low-level client returned by __enter__
            assert captured['client'] is client_ctx
            assert captured['index_name'] == 'idx'
            assert captured['text_key'] == 'text'
            assert captured['use_multi_tenancy'] is False

        # __exit__ should call DummyClientContext.__exit__ (no exception)
        ev.__exit__(None, None, None)
        assert client_ctx.exited_args == (None, None, None)
