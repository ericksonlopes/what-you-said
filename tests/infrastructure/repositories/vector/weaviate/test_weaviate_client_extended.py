import pytest
import sys
from unittest.mock import MagicMock
from src.infrastructure.repositories.vector.weaviate.weaviate_client import (
    WeaviateClient,
)


class DummyConfig:
    def __init__(self, api_key=None):
        self.weaviate_host = "localhost"
        self.weaviate_port = 8080
        self.weaviate_grpc_port = 8090
        self.weaviate_api_key = api_key
        self.weaviate_url = "http://localhost:8080"


class FakeClient:
    def __init__(self, ready=True):
        self.closed = False
        self._ready = ready
        self.collections = MagicMock()

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
class TestWeaviateClientExtended:
    def setup_mocks(self, monkeypatch):
        mock_weaviate = MagicMock()
        monkeypatch.setitem(sys.modules, "weaviate", mock_weaviate)
        mock_auth = MagicMock()
        monkeypatch.setitem(sys.modules, "weaviate.classes.init", mock_auth)
        mock_config = MagicMock()
        monkeypatch.setitem(sys.modules, "weaviate.classes.config", mock_config)
        return mock_weaviate, mock_auth, mock_config

    def test_create_client_cloud_success(self, monkeypatch):
        mock_weaviate, mock_auth, _ = self.setup_mocks(monkeypatch)
        fake = FakeClient()
        mock_weaviate.connect_to_weaviate_cloud.return_value = fake

        cfg = DummyConfig(api_key="secret")
        wc = WeaviateClient(cfg)
        client = wc._create_client()
        assert client is fake
        mock_weaviate.connect_to_weaviate_cloud.assert_called_once()

    def test_exit_exception_during_close(self, monkeypatch):
        mock_weaviate, _, _ = self.setup_mocks(monkeypatch)
        fake = FakeClient()
        fake.close = MagicMock(side_effect=Exception("Close error"))
        mock_weaviate.connect_to_local.return_value = fake

        wc = WeaviateClient(DummyConfig())
        with wc:
            pass

        assert wc._client is None  # Should be cleared anyway

    def test_create_collection_if_not_exists(self, monkeypatch):
        mock_weaviate, _, mock_wvc = self.setup_mocks(monkeypatch)
        fake = FakeClient()
        mock_weaviate.connect_to_local.return_value = fake

        # 1. Test collection exists
        fake.collections.exists.return_value = True
        wc = WeaviateClient(DummyConfig())
        wc.create_collection_if_not_exists("Existing")
        fake.collections.create.assert_not_called()

        # 2. Test collection doesn't exist
        fake.collections.exists.return_value = False
        wc.create_collection_if_not_exists("New")
        fake.collections.create.assert_called_once()
