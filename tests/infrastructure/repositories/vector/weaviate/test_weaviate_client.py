import sys
from unittest.mock import MagicMock

import pytest

from src.infrastructure.repositories.vector.weaviate.weaviate_client import (
    WeaviateClient,
)


class DummyConfig:
    weaviate_host = "localhost"
    weaviate_port = 8080
    weaviate_grpc_port = 8090
    weaviate_api_key = None
    weaviate_url = "http://localhost:8080"


class FakeClient:
    def __init__(self, ready=True):
        self.closed = False
        self._ready = ready

    def is_ready(self):
        return self._ready

    def is_live(self):
        return True

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.close()


@pytest.mark.WeaviateClient
class TestWeaviateClient:
    def test_create_client_local_success(self, monkeypatch):
        mock_weaviate = MagicMock()
        fake = FakeClient()
        mock_weaviate.connect_to_local.return_value = fake
        monkeypatch.setitem(sys.modules, "weaviate", mock_weaviate)
        # Mocking Auth to avoid import errors if weaviate is not installed
        mock_auth = MagicMock()
        monkeypatch.setitem(sys.modules, "weaviate.classes.init", mock_auth)

        cfg = DummyConfig()
        wc = WeaviateClient(cfg, env="testing")
        client = wc._create_client()
        assert client is fake
        mock_weaviate.connect_to_local.assert_called_once()

    def test_create_client_not_ready_raises(self, monkeypatch):
        mock_weaviate = MagicMock()
        mock_weaviate.connect_to_local.return_value = FakeClient(ready=False)
        monkeypatch.setitem(sys.modules, "weaviate", mock_weaviate)
        mock_auth = MagicMock()
        monkeypatch.setitem(sys.modules, "weaviate.classes.init", mock_auth)

        cfg = DummyConfig()
        wc = WeaviateClient(cfg, env="testing")
        with pytest.raises(ConnectionError):
            wc._create_client()

    def test_context_manager_calls_close(self, monkeypatch):
        mock_weaviate = MagicMock()
        fake = FakeClient()
        mock_weaviate.connect_to_local.return_value = fake
        monkeypatch.setitem(sys.modules, "weaviate", mock_weaviate)
        mock_auth = MagicMock()
        monkeypatch.setitem(sys.modules, "weaviate.classes.init", mock_auth)

        cfg = DummyConfig()
        wc = WeaviateClient(cfg, env="testing")
        with wc as client:
            assert client.is_ready()

        # After context exit, internal client should be cleared
        assert wc._client is None
        assert fake.closed is True
