import pytest
from unittest.mock import MagicMock, patch
from src.infrastructure.services.model_loader_service import ModelLoaderService


@pytest.fixture(autouse=True)
def clear_cache():
    ModelLoaderService._model_cache = {}


@pytest.mark.Dependencies
class TestModelLoaderService:
    def test_load_model_success(self):
        with patch(
            "src.infrastructure.services.model_loader_service.SentenceTransformer"
        ) as mock_st:
            mock_model = MagicMock()
            mock_st.return_value = mock_model

            service = ModelLoaderService("test-model")

            assert service.model_name == "test-model"
            assert "test-model" in ModelLoaderService._model_cache
            assert service.model == mock_model
            mock_st.assert_called_once()

    def test_load_model_failure(self):
        with patch(
            "src.infrastructure.services.model_loader_service.SentenceTransformer",
            side_effect=Exception("Load error"),
        ):
            with pytest.raises(RuntimeError, match="Failed to load models"):
                ModelLoaderService("fail-model")

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
            with pytest.raises(
                RuntimeError, match="Failed to determine model embedding dimensions"
            ):
                _ = service.dimensions

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
            # Remove max_seq_length if it exists to test default
            if hasattr(mock_model, "max_seq_length"):
                del mock_model.max_seq_length
            mock_st.return_value = mock_model

            service = ModelLoaderService("test-model")
            # Default is 512 in the code
            assert service.max_seq_length == 512

    def test_cuda_device(self):
        with patch("torch.cuda.is_available", return_value=True):
            with patch(
                "src.infrastructure.services.model_loader_service.SentenceTransformer"
            ):
                service = ModelLoaderService("test-model")
                assert service.device == "cuda"

    def test_cpu_device(self):
        with patch("torch.cuda.is_available", return_value=False):
            with patch(
                "src.infrastructure.services.model_loader_service.SentenceTransformer"
            ):
                service = ModelLoaderService("test-model")
                assert service.device == "cpu"
