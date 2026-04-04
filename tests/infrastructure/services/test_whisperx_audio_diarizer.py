from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from src.infrastructure.services.whisperx_audio_diarizer import AudioDiarizer  # noqa: E402


@pytest.mark.AudioDiarizer
class TestAudioDiarizer:
    @pytest.fixture(autouse=True)
    def mock_whisperx(self):
        with patch(
            "src.infrastructure.services.whisperx_audio_diarizer.whisperx"
        ) as mock:
            self.whisperx = mock
            yield

    @patch("src.infrastructure.services.whisperx_audio_diarizer.load_whisperx_audio")
    @patch("os.path.exists")
    @patch("torch.set_num_threads")
    def test_run_diarization_pipeline(self, mock_torch, mock_exists, mock_load_audio):
        mock_exists.return_value = True
        mock_load_audio.return_value = np.zeros(16000)

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
                        [Segment(start=0.0, end=1.0, text="test", speaker="S0")],
                        "en",
                    )

                    diarizer = AudioDiarizer(hf_token="fake", model_size="tiny")
                    result = diarizer.run("dummy.wav")
                    assert result.language == "en"
                    assert len(result.segments) == 1

    def test_transcribe_internal(self):
        mock_model = MagicMock()
        self.whisperx.load_model.return_value = mock_model
        mock_model.transcribe.return_value = {"segments": [], "language": "en"}

        diarizer = AudioDiarizer(hf_token="f")
        with patch(
            "src.infrastructure.services.whisperx_audio_diarizer.load_whisperx_audio",
            return_value=np.zeros(10),
        ):
            result, _ = diarizer._transcribe("f.wav", "en")
            assert result["language"] == "en"
            self.whisperx.load_model.assert_called_once()

    def test_align_internal(self):
        self.whisperx.load_align_model.return_value = (MagicMock(), MagicMock())
        self.whisperx.align.return_value = {"segments": []}

        diarizer = AudioDiarizer(hf_token="f")
        result = diarizer._align({"segments": []}, np.zeros(100), "en")
        assert "segments" in result

    def test_diarize_internal(self):
        with patch(
            "src.infrastructure.services.whisperx_audio_diarizer.load_whisperx_audio",
            return_value=np.zeros(10),
        ):
            mock_pipeline_cls = MagicMock()
            # Since whisperx.diarize.DiarizationPipeline is imported INSIDE _diarize, handle it
            with patch("whisperx.diarize.DiarizationPipeline", mock_pipeline_cls):
                self.whisperx.assign_word_speakers.return_value = {
                    "segments": [{"start": 0, "end": 1, "text": "t", "speaker": "S1"}]
                }

                diarizer = AudioDiarizer(hf_token="fake")
                segments, _ = diarizer._diarize(
                    "f.wav", {"segments": []}, 1, None, None
                )
                assert len(segments) == 1
