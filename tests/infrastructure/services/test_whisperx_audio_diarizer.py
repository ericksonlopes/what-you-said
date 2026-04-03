import sys
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

# Mocking whisperx and torch at module level if they are heavy/optional
mock_whisperx = MagicMock()
sys.modules["whisperx"] = mock_whisperx
sys.modules["whisperx.diarize"] = MagicMock()

from src.infrastructure.services.whisperx_audio_diarizer import AudioDiarizer

@pytest.mark.AudioDiarizer
class TestAudioDiarizer:
    @patch("src.infrastructure.services.whisperx_audio_diarizer.load_whisperx_audio")
    @patch("os.path.exists")
    @patch("torch.set_num_threads")
    def test_run_diarization_pipeline(self, mock_torch, mock_exists, mock_load_audio):
        mock_exists.return_value = True
        mock_load_audio.return_value = np.zeros(16000)
        
        # Setup whisperx mocks
        mock_model = MagicMock()
        mock_whisperx.load_model.return_value = mock_model
        mock_model.transcribe.return_value = {
            "segments": [{"start": 0.0, "end": 1.0, "text": "test"}],
            "language": "en"
        }
        
        mock_whisperx.load_align_model.return_value = (MagicMock(), {})
        mock_whisperx.align.return_value = {
            "segments": [{"start": 0.0, "end": 1.0, "text": "test", "speaker": "SPEAKER_00"}],
            "language": "en"
        }
        
        with patch("whisperx.diarize.DiarizationPipeline") as mock_pipeline:
            mock_pipe_instance = MagicMock()
            mock_pipeline.return_value = mock_pipe_instance
            mock_pipe_instance.return_value = [] # diarize_segments
            
            with patch("whisperx.assign_word_speakers") as mock_assign:
                mock_assign.return_value = {
                    "segments": [{"start": 0.0, "end": 1.0, "text": "test", "speaker": "SPEAKER_00"}],
                    "language": "en"
                }
                
                diarizer = AudioDiarizer(hf_token="fake_token", model_size="tiny")
                result = diarizer.run("dummy.wav")
                
                assert result.language == "en"
                assert len(result.segments) == 1
                assert result.segments[0].speaker == "SPEAKER_00"
