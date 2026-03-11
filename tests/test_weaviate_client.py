import pytest

from src.infrastructure.repository.weaviate.weaviate_client import WeaviateClient


class DummyConfig:
    host = "localhost"
    port = 8080
    grpc_port = 8090
    api_key = "key"


class FakeClient:
    def __init__(self):
        self.closed = False

    def is_ready(self):
        return True

    def is_live(self):
        return True

    def close(self):
        self.closed = True


@pytest.mark.WeaviateClient
class TestWeaviateClient:
    def test_create_client_local_success(self, monkeypatch):
        def fake_connect_to_local(host, port, grpc_port):
            return FakeClient()

        monkeypatch.setattr(
            "src.infrastructure.repository.weaviate.weaviate_client.weaviate.connect_to_local",
            fake_connect_to_local,
        )

        cfg = DummyConfig()
        wc = WeaviateClient(cfg, env="testing")
        client = wc._create_client()
        assert isinstance(client, FakeClient)

    def test_create_client_not_ready_raises(self, monkeypatch):
        class BadClient:
            def is_ready(self):
                return False

            def is_live(self):
                return True

        monkeypatch.setattr(
            "src.infrastructure.repository.weaviate.weaviate_client.weaviate.connect_to_local",
            lambda host, port, grpc_port: BadClient(),
        )

        cfg = DummyConfig()
        wc = WeaviateClient(cfg, env="testing")
        with pytest.raises(ConnectionError):
            wc._create_client()

    def test_context_manager_calls_close(self, monkeypatch):
        class FakeClient2:
            def __init__(self):
                self.closed = False

            def is_ready(self):
                return True

            def is_live(self):
                return True

            def close(self):
                self.closed = True

        monkeypatch.setattr(
            "src.infrastructure.repository.weaviate.weaviate_client.weaviate.connect_to_local",
            lambda host, port, grpc_port: FakeClient2(),
        )

        cfg = DummyConfig()
        wc = WeaviateClient(cfg, env="testing")
        with wc as client:
            assert client.is_ready()
        # After context exit, internal client should be cleared
        assert wc._client is None
