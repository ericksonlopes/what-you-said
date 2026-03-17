import types
import pytest


@pytest.mark.ModelLoaderService
class TestModelLoaderService:
    def test_load_model_success(self, monkeypatch):
        class FakeSentenceTransformer:
            def __init__(self, name, device):
                self.name = name
                self.device = device

        monkeypatch.setattr(
            "src.infrastructure.services.model_loader_service.SentenceTransformer",
            FakeSentenceTransformer,
        )
        # force cpu path
        monkeypatch.setattr(
            "src.infrastructure.services.model_loader_service.torch",
            types.SimpleNamespace(
                cuda=types.SimpleNamespace(is_available=lambda: False)
            ),
        )

        from src.infrastructure.services.model_loader_service import ModelLoaderService

        # Clear cache for isolated test
        ModelLoaderService._model_cache = {}

        svc = ModelLoaderService("test-models")
        assert hasattr(svc, "model")
        assert svc.model.name == "test-models"
        assert svc.model.device == "cpu"

    def test_load_model_failure(self, monkeypatch):
        class BadSentenceTransformer:
            def __init__(self, name, device):
                raise RuntimeError("boom")

        monkeypatch.setattr(
            "src.infrastructure.services.model_loader_service.SentenceTransformer",
            BadSentenceTransformer,
        )

        monkeypatch.setattr(
            "src.infrastructure.services.model_loader_service.torch",
            types.SimpleNamespace(
                cuda=types.SimpleNamespace(is_available=lambda: False)
            ),
        )

        from src.infrastructure.services.model_loader_service import ModelLoaderService

        with pytest.raises(RuntimeError):
            ModelLoaderService("bad")
