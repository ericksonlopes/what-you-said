from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.services.model_loader_service import ModelLoaderService


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset Singleton for each test."""
    ModelLoaderService._instance = None
    ModelLoaderService._models = {}
    ModelLoaderService._initialized = False


@pytest.mark.Dependencies
class TestModelLoaderService:
    def test_load_model_success(self):
        with patch(
            "src.infrastructure.services.model_loader_service.SentenceTransformer"
        ) as mock_st:
            mock_model = MagicMock()
            mock_st.return_value = mock_model

            service = ModelLoaderService("test-model")
            service.load_model()

            assert service.model_name == "test-model"
            # _embedding_model is instance attribute, not in _models dict
            assert service._embedding_model == mock_model
            assert service.model == mock_model
            mock_st.assert_called_once()

    def test_load_model_failure(self):
        with patch(
            "src.infrastructure.services.model_loader_service.SentenceTransformer",
            side_effect=Exception("Load error"),
        ):
            service = ModelLoaderService("fail-model")
            # SentenceTransformer is called inside load_model and it raises Exception
            with pytest.raises(Exception, match="Load error"):
                service.load_model()

    def test_dimensions_property(self):
        with patch(
            "src.infrastructure.services.model_loader_service.SentenceTransformer"
        ) as mock_st:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_st.return_value = mock_model

            service = ModelLoaderService("test-model")
            assert service.dimensions == 384

    def test_dimensions_property_failure(self):
        with patch(
            "src.infrastructure.services.model_loader_service.SentenceTransformer"
        ) as mock_st:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = None
            mock_st.return_value = mock_model

            service = ModelLoaderService("test-model")
            # My current implementation returns 0 if None
            assert service.dimensions == 0

    def test_max_seq_length_property(self):
        with patch(
            "src.infrastructure.services.model_loader_service.SentenceTransformer"
        ) as mock_st:
            mock_model = MagicMock()
            mock_model.max_seq_length = 512
            mock_st.return_value = mock_model

            service = ModelLoaderService("test-model")
            assert service.max_seq_length == 512

    def test_max_seq_length_property_default(self):
        with patch(
            "src.infrastructure.services.model_loader_service.SentenceTransformer"
        ) as mock_st:
            mock_model = MagicMock()
            # My implementation uses getattr with default 0
            if hasattr(mock_model, "max_seq_length"):
                del mock_model.max_seq_length
            mock_st.return_value = mock_model

            service = ModelLoaderService("test-model")
            assert service.max_seq_length == 0
