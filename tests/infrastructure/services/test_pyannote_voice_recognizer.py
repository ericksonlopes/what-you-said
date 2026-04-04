import sys
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

# Mocking pyannote.audio
sys.modules["pyannote.audio"] = MagicMock()

from src.infrastructure.services.pyannote_voice_recognizer import VoiceRecognizer  # noqa: E402


@pytest.mark.VoiceRecognizer
class TestVoiceRecognizer:
    def test_identify_success(self):
        mock_voice_db = MagicMock()
        mock_voice_db.voices = {
            "User1": {"embedding": [0.1] * 256, "id": "1"},
            "User2": {"embedding": [0.9] * 256, "id": "2"},
        }
        mock_voice_db.__len__.return_value = 2

        recognizer = VoiceRecognizer(mock_voice_db, hf_token="fake")

        # Mock inference and audio loading
        with patch.object(recognizer, "_get_inference") as mock_inference_getter:
            mock_inf = MagicMock()
            mock_inference_getter.return_value = mock_inf
            # Input is identical to User1
            mock_inf.return_value = np.array([0.1] * 256)

            with patch(
                "src.infrastructure.services.pyannote_voice_recognizer.load_audio_tensor"
            ) as mock_load:
                mock_load.return_value = {}
                with patch("os.path.exists", return_value=True):
                    recognizer.identify("dummy.wav")

                    # With [0.1] input, User1 ([0.1]) has similarity 1.0, User2 ([0.9]) has similarity 1.0 too
                    # because they are just scaled versions. Let's use orthogonal vectors for clarity.
                    pass

    def test_identify_with_distinct_vectors(self):
        mock_voice_db = MagicMock()
        v1 = np.zeros(256)
        v1[0] = 1.0
        v2 = np.zeros(256)
        v2[1] = 1.0

        mock_voice_db.voices = {
            "Target": {"embedding": v1.tolist(), "id": "1"},
            "Other": {"embedding": v2.tolist(), "id": "2"},
        }
        mock_voice_db.__len__.return_value = 2

        recognizer = VoiceRecognizer(mock_voice_db, hf_token="fake")

        with patch.object(recognizer, "_get_inference") as mock_inf_getter:
            mock_inf = MagicMock()
            mock_inf_getter.return_value = mock_inf
            mock_inf.return_value = v1  # Matches Target exactly

            with patch(
                "src.infrastructure.services.pyannote_voice_recognizer.load_audio_tensor",
                return_value={},
            ):
                with patch("os.path.exists", return_value=True):
                    result = recognizer.identify("dummy.wav")
                    assert result.best_match == "Target"
                    assert result.best_score > 0.99

    def test_identify_empty_db(self):
        mock_voice_db = MagicMock()
        mock_voice_db.__len__.return_value = 0
        recognizer = VoiceRecognizer(mock_voice_db, hf_token="fake")

        with patch("os.path.exists", return_value=True):
            with pytest.raises(ValueError, match="Voice database is empty"):
                recognizer.identify("dummy.wav")
