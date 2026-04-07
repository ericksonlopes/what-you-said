from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.infrastructure.services.pyannote_voice_recognizer import VoiceRecognizer


@pytest.mark.VoiceRecognizer
class TestVoiceRecognizer:
    def test_identify_success(self, sqlite_memory):
        mock_voice_db = MagicMock()
        mock_voice_db.voices = {"U1": {"embedding": [0.1] * 256, "id": "1"}}
        mock_voice_db.__len__.return_value = 1
        recognizer = VoiceRecognizer(mock_voice_db, hf_token="f")

        with patch.object(recognizer, "_get_inference") as mock_inf_getter:
            mock_inf = MagicMock()
            mock_inf_getter.return_value = mock_inf
            mock_inf.return_value = np.array([0.1] * 256)
            with patch(
                "src.infrastructure.services.pyannote_voice_recognizer.load_audio_tensor",
                return_value=np.zeros(10),
            ):
                with patch("os.path.exists", return_value=True):
                    res = recognizer.identify("d.wav")
                    assert res.best_match == "U1"

    def test_identify_with_distinct_vectors(self):
        mock_vdb = MagicMock()
        v1, v2 = np.zeros(256), np.zeros(256)
        v1[0], v2[1] = 1.0, 1.0
        mock_vdb.voices = {
            "T": {"embedding": v1.tolist(), "id": "1"},
            "O": {"embedding": v2.tolist(), "id": "2"},
        }
        mock_vdb.__len__.return_value = 2
        recognizer = VoiceRecognizer(mock_vdb, hf_token="f")
        with patch.object(recognizer, "_get_inference") as mk:
            mk.return_value = lambda x: v1  # matches T
            with patch(
                "src.infrastructure.services.pyannote_voice_recognizer.load_audio_tensor",
                return_value=np.zeros(10),
            ):
                with patch("os.path.exists", return_value=True):
                    res = recognizer.identify("d.wav")
                    assert res.best_match == "T"

    def test_identify_empty_db(self):
        recognizer = VoiceRecognizer(MagicMock(__len__=lambda x: 0), hf_token="f")
        with patch("os.path.exists", return_value=True):
            with pytest.raises(ValueError, match="empty"):
                recognizer.identify("d.wav")

    def test_init_device_auto(self):
        with patch(
            "src.infrastructure.services.pyannote_voice_recognizer.get_best_device",
            return_value="cpu",
        ):
            recognizer = VoiceRecognizer(MagicMock(), hf_token="f")
            assert recognizer._device == "cpu"

    def test_identify_dir(self):
        mock_vdb = MagicMock()
        mock_vdb.voices = {"A": {"embedding": [0.1] * 256, "id": "1"}}
        mock_vdb.__len__.return_value = 1
        recognizer = VoiceRecognizer(mock_vdb, hf_token="f")
        with patch("os.path.isdir", return_value=True):
            mock_path = MagicMock()
            mock_path.name = "s1.wav"
            mock_path.stem = "s1"
            with patch("pathlib.Path.glob", return_value=[mock_path]):
                with patch.object(recognizer, "_get_inference") as mock_inf_getter:
                    mock_inf = MagicMock()
                    mock_inf_getter.return_value = mock_inf
                    mock_inf.return_value = np.array([0.1] * 256)
                    with patch(
                        "src.infrastructure.services.pyannote_voice_recognizer.load_audio_tensor",
                        return_value=np.zeros(10),
                    ):
                        res = recognizer.identify_dir("/tmp")
                        assert res.results["s1"].best_match == "A"

    def test_get_inference_internal(self):
        with patch(
            "src.infrastructure.services.pyannote_voice_recognizer.model_loader"
        ) as mock_loader:
            mock_loader.get_voice_inference.return_value = MagicMock()
            recognizer = VoiceRecognizer(MagicMock(), hf_token="f")
            inf = recognizer._get_inference()
            assert inf is not None
            mock_loader.get_voice_inference.assert_called_once_with(
                hf_token="f", device=recognizer._device
            )
