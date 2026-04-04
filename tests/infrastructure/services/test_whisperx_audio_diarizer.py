import sys
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

# Mocking whisperx and torch at module level to avoid heavy imports
sys.modules["whisperx"] = MagicMock()
sys.modules["whisperx.diarize"] = MagicMock()
sys.modules["whisperx.asr"] = MagicMock()

from src.infrastructure.services.whisperx_audio_diarizer import AudioDiarizer  # noqa: E402


@pytest.mark.AudioDiarizer
class TestAudioDiarizer:
    @patch("src.infrastructure.services.whisperx_audio_diarizer.load_whisperx_audio")
    @patch("os.path.exists")
    @patch("torch.set_num_threads")
    def test_run_diarization_pipeline(self, mock_torch, mock_exists, mock_load_audio):
        mock_exists.return_value = True
        mock_load_audio.return_value = np.zeros(16000)

        # Instead of mocking the whole whisperx library and its internal calls,
        # let's mock the private methods of AudioDiarizer which are the ones
        # that actually interact with whisperx.

        with patch.object(AudioDiarizer, "_transcribe") as mock_trans:
            mock_trans.return_value = (
                {"language": "en", "segments": []},
                np.zeros(100),
            )

            with patch.object(AudioDiarizer, "_align") as mock_align:
                mock_align.return_value = {"language": "en", "segments": []}

                with patch.object(AudioDiarizer, "_diarize") as mock_diarize:
                    from src.domain.entities.diarization import Segment

                    mock_diarize.return_value = (
                        [
                            Segment(
                                start=0.0, end=1.0, text="test", speaker="SPEAKER_00"
                            )
                        ],
                        "en",
                    )

                    diarizer = AudioDiarizer(hf_token="fake_token", model_size="tiny")
                    result = diarizer.run("dummy.wav")

                    assert result.language == "en"
                    assert len(result.segments) == 1
                    assert result.segments[0].speaker == "SPEAKER_00"
                    assert result.audio_path == "dummy.wav"
