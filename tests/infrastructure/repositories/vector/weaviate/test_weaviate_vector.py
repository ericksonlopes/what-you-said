import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.infrastructure.repositories.vector.weaviate.weaviate_vector import (
    WeaviateVector,
)


class DummyClientContext:
    def __init__(self):
        self.entered = False
        self.exited_args = None

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, exc_type, exc, tb):
        self.exited_args = (exc_type, exc, tb)

    def create_collection_if_not_exists(self, collection_name, dimensions=None):
        pass


class DummyEmbedding:
    def __init__(self, dimensions=768):
        self.model_loader_service = SimpleNamespace(dimensions=dimensions)


@pytest.mark.WeaviateVector
class TestWeaviateVector:
    def test_enter_returns_weaviate_vector_store(self, monkeypatch):
        captured = {}

        class FakeWeaviateVectorStore:
            def __init__(
                self, client, index_name, text_key, embedding, use_multi_tenancy
            ):
                captured["client"] = client
                captured["index_name"] = index_name
                captured["text_key"] = text_key
                captured["embedding"] = embedding
                captured["use_multi_tenancy"] = use_multi_tenancy

            def as_retriever(self, **kwargs):
                return SimpleNamespace(invoke=lambda q: [])

        # Mock the lazy-loaded module
        mock_langchain_weaviate = MagicMock()
        mock_langchain_weaviate.WeaviateVectorStore = FakeWeaviateVectorStore
        monkeypatch.setitem(sys.modules, "langchain_weaviate", mock_langchain_weaviate)

        client_ctx = DummyClientContext()
        ev = WeaviateVector(
            client=client_ctx,
            embedding_service=DummyEmbedding(),
            index_name="idx",
            text_key="text",
            use_multi_tenancy=False,
        )

        with ev as store:
            assert isinstance(store, FakeWeaviateVectorStore)
            # ensure FakeWeaviateVectorStore was constructed with the low-level client returned by __enter__
            assert captured["client"] is client_ctx
            assert captured["index_name"] == "idx"
            assert captured["text_key"] == "text"
            assert captured["use_multi_tenancy"] is False

        # __exit__ should call DummyClientContext.__exit__ (no exception)
        assert client_ctx.exited_args == (None, None, None)
