from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.infrastructure.services.whisperx_audio_diarizer import AudioDiarizer


@pytest.mark.AudioDiarizer
class TestAudioDiarizer:
    @pytest.fixture(autouse=True)
    def mock_deps(self):
        with patch("src.infrastructure.services.whisperx_audio_diarizer.model_loader") as ml:
            self.mock_model_loader = ml
            with patch("src.infrastructure.services.whisperx_audio_diarizer.whisperx") as wx:
                self.whisperx = wx
                yield

    @patch("src.infrastructure.services.whisperx_audio_diarizer.load_whisperx_audio")
    @patch("os.path.exists")
    def test_run_diarization_pipeline(self, mock_exists, mock_load_audio):
        mock_exists.return_value = True
        mock_load_audio.return_value = np.zeros(16000)

        with patch.object(AudioDiarizer, "_transcribe") as mock_trans:
            mock_trans.return_value = {"language": "en", "segments": []}
            with patch.object(AudioDiarizer, "_align") as mock_align:
                mock_align.return_value = {"language": "en", "segments": []}
                with patch.object(AudioDiarizer, "_diarize") as mock_diarize:
                    from src.domain.entities.diarization import Segment

                    mock_diarize.return_value = (
                        [Segment(start=0.0, end=1.0, text="test", speaker="S0")],
                        "en",
                    )

                    diarizer = AudioDiarizer(hf_token="fake", model_size="tiny")
                    result = diarizer.run("dummy.wav")
                    assert result.language == "en"
                    assert len(result.segments) == 1

    def test_transcribe_internal(self):
        mock_model = MagicMock()
        self.mock_model_loader.get_whisper_model.return_value = mock_model
        mock_model.transcribe.return_value = {"segments": [], "language": "en"}

        diarizer = AudioDiarizer(hf_token="f")
        audio_data = np.zeros(10)
        result = diarizer._transcribe(audio_data, "en")

        assert result["language"] == "en"
        self.mock_model_loader.get_whisper_model.assert_called_once()

    def test_align_internal(self):
        mock_align_model = MagicMock()
        self.mock_model_loader.get_align_model.return_value = (
            mock_align_model,
            MagicMock(),
        )
        self.whisperx.align.return_value = {"segments": []}

        diarizer = AudioDiarizer(hf_token="f")
        result = diarizer._align({"segments": []}, np.zeros(100), "en")
        assert "segments" in result
        self.mock_model_loader.get_align_model.assert_called_once()

    def test_diarize_internal(self):
        self.mock_model_loader.get_diarization_pipeline.return_value = MagicMock()
        self.whisperx.assign_word_speakers.return_value = {
            "segments": [{"start": 0, "end": 1, "text": "t", "speaker": "S1"}]
        }

        diarizer = AudioDiarizer(hf_token="fake")
        audio_data = np.zeros(10)
        segments, _ = diarizer._diarize(audio_data, {"segments": []}, 1, None, None)
        assert len(segments) == 1
        self.mock_model_loader.get_diarization_pipeline.assert_called_once()
