import pytest
from unittest.mock import MagicMock, patch
from src.application.use_cases.process_audio_diarization_pipeline import ProcessAudioDiarizationPipelineUseCase
from src.domain.entities.diarization import DiarizationResult

@pytest.mark.ProcessAudioDiarizationPipeline
class TestProcessAudioDiarizationPipeline:
    @patch("src.application.use_cases.process_audio_diarization_pipeline.StorageService")
    @patch("src.application.use_cases.process_audio_diarization_pipeline.AudioDownloader")
    @patch("src.application.use_cases.process_audio_diarization_pipeline.AudioDiarizer")
    @patch("src.application.use_cases.process_audio_diarization_pipeline.VoiceDB")
    @patch("os.makedirs")
    @patch("os.replace")
    @patch("shutil.rmtree")
    def test_execute_youtube_success(self, mock_rmtree, mock_replace, mock_makedirs, 
                                     mock_voice_db_cls, mock_diarizer_cls, 
                                     mock_downloader_cls, mock_storage_cls, sqlite_memory):
        
        # Setup mocks
        mock_downloader = mock_downloader_cls.return_value
        mock_downloader.download.return_value = "/tmp/audio.mp3"
        
        mock_diarizer = mock_diarizer_cls.return_value
        mock_diarization_result = MagicMock(spec=DiarizationResult)
        mock_diarization_result.segments = []
        mock_diarization_result.speakers = set()
        mock_diarization_result.duration = 10.0
        mock_diarization_result.language = "pt"
        mock_diarizer.run.return_value = mock_diarization_result
        
        # Mock repository save
        mock_record = MagicMock()
        mock_record.id = "uuid-123"
        with patch("src.infrastructure.repositories.sql.repositories.DiarizationRepository.save", return_value=mock_record):
            use_case = ProcessAudioDiarizationPipelineUseCase(sqlite_memory)
            
            result = use_case.execute(
                source_type="youtube",
                source="https://youtube.com/watch?v=test",
                recognize_voices=True
            )
            
            assert result["title"] == "audio"
            assert result["storage_path"] == "processed/uuid-123/recognition"
        assert mock_downloader.download.called
        assert mock_diarizer.run.called
