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
            'src.infrastructure.services.model_loader_service.SentenceTransformer',
            FakeSentenceTransformer,
        )
        # force cpu path
        monkeypatch.setattr(
            'src.infrastructure.services.model_loader_service.torch',
            types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False)),
        )

        from src.infrastructure.services.model_loader_service import ModelLoaderService

        svc = ModelLoaderService("test-models")
        assert hasattr(svc, 'model_instance')
        assert isinstance(svc.model_instance, FakeSentenceTransformer)
        assert svc.model.name == "test-models"


    def test_load_model_failure(self, monkeypatch):
        class BadSentenceTransformer:
            def __init__(self, name, device):
                raise RuntimeError("boom")

        monkeypatch.setattr(
            'src.infrastructure.services.model_loader_service.SentenceTransformer',
            BadSentenceTransformer,
        )

        monkeypatch.setattr(
            'src.infrastructure.services.model_loader_service.torch',
            types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False)),
        )

        from src.infrastructure.services.model_loader_service import ModelLoaderService

        with pytest.raises(RuntimeError):
            ModelLoaderService("bad")
