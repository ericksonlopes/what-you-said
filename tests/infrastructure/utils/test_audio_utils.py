import numpy as np
import pytest
import torch
from unittest.mock import patch
from src.infrastructure.utils.audio_utils import (
    load_audio_tensor,
    load_whisperx_audio,
    cosine_similarity,
    get_best_device,
)


@pytest.mark.AudioUtils
class TestAudioUtils:
    @patch("soundfile.read")
    @patch("os.path.exists")
    def test_load_audio_tensor_wav(self, mock_exists, mock_sf_read):
        # Mocking soundfile.read to return a mono 16kHz audio
        mock_data = np.random.rand(16000, 1).astype(np.float32)
        mock_sf_read.return_value = (mock_data, 16000)
        mock_exists.return_value = True

        result = load_audio_tensor("dummy.wav")

        assert "waveform" in result
        assert result["sample_rate"] == 16000
        assert isinstance(result["waveform"], torch.Tensor)
        assert result["waveform"].shape[0] == 1  # Mono

    @patch("soundfile.read")
    def test_load_audio_tensor_resample(self, mock_sf_read):
        # Mocking 44.1kHz audio, should be resampled to 16kHz
        mock_data = np.random.rand(44100, 1).astype(np.float32)
        mock_sf_read.return_value = (mock_data, 44100)

        with patch("torchaudio.functional.resample") as mock_resample:
            mock_resample.return_value = torch.randn(1, 16000)
            load_audio_tensor("dummy.wav")
            assert mock_resample.called

    @patch("soundfile.read")
    def test_load_whisperx_audio(self, mock_sf_read):
        mock_data = np.random.rand(16000, 1).astype(np.float32)
        mock_sf_read.return_value = (mock_data, 16000)

        result = load_whisperx_audio("dummy.wav")
        assert isinstance(result, np.ndarray)
        assert result.ndim == 1

    def test_cosine_similarity(self):
        a = np.array([1, 0])
        b = np.array([1, 0])
        assert cosine_similarity(a, b) == pytest.approx(1.0)

        c = np.array([0, 1])
        assert cosine_similarity(a, c) == pytest.approx(0.0)

    @patch("torch.cuda.is_available")
    def test_get_best_device(self, mock_cuda):
        mock_cuda.return_value = True
        assert get_best_device() == "cuda"

        mock_cuda.return_value = False
        assert get_best_device() == "cpu"
