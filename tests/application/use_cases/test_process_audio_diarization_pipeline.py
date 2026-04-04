import pytest
from unittest.mock import MagicMock, patch
from src.application.use_cases.process_audio_diarization_pipeline import (
    ProcessAudioDiarizationPipelineUseCase,
)
from src.domain.entities.diarization import DiarizationResult


@pytest.mark.ProcessAudioDiarizationPipeline
class TestProcessAudioDiarizationPipeline:
    @patch(
        "src.application.use_cases.process_audio_diarization_pipeline.StorageService"
    )
    @patch(
        "src.application.use_cases.process_audio_diarization_pipeline.YoutubeExtractor"
    )
    @patch("src.application.use_cases.process_audio_diarization_pipeline.AudioDiarizer")
    @patch("src.application.use_cases.process_audio_diarization_pipeline.VoiceDB")
    @patch("os.makedirs")
    @patch("os.replace")
    @patch("shutil.rmtree")
    def test_execute_youtube_success(
        self,
        mock_rmtree,
        mock_replace,
        mock_makedirs,
        mock_voice_db_cls,
        mock_diarizer_cls,
        mock_extractor_cls,
        mock_storage_cls,
        sqlite_memory,
    ):

        # Setup mocks
        mock_extractor = mock_extractor_cls.return_value
        mock_extractor.download_audio.return_value = "/tmp/audio.mp3"
        mock_extractor.extract_metadata.return_value = MagicMock()

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
        with patch(
            "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.save",
            return_value=mock_record,
        ):
            use_case = ProcessAudioDiarizationPipelineUseCase(sqlite_memory)

            result = use_case.execute(
                source_type="youtube",
                source="https://youtube.com/watch?v=test",
                recognize_voices=True,
            )

            assert result["title"] == "audio"
            assert result["storage_path"] == "processed/uuid-123/recognition"
        assert mock_extractor.download_audio.called
        assert mock_diarizer.run.called

    @patch(
        "src.application.use_cases.process_audio_diarization_pipeline.StorageService"
    )
    @patch(
        "src.application.use_cases.process_audio_diarization_pipeline.YoutubeExtractor"
    )
    @patch("src.application.use_cases.process_audio_diarization_pipeline.AudioDiarizer")
    @patch("src.application.use_cases.process_audio_diarization_pipeline.VoiceDB")
    @patch("os.makedirs")
    @patch("os.replace")
    @patch("shutil.rmtree")
    @patch("os.path.exists", return_value=True)
    def test_execute_upload_success(
        self,
        mock_exists,
        mock_rmtree,
        mock_replace,
        mock_makedirs,
        mock_voice_db_cls,
        mock_diarizer_cls,
        mock_extractor_cls,
        mock_storage_cls,
        sqlite_memory,
    ):
        mock_storage = mock_storage_cls.return_value
        mock_storage.bucket = "test-bucket"

        mock_diarizer = mock_diarizer_cls.return_value
        mock_diarization_result = MagicMock(spec=DiarizationResult)
        mock_diarizer.run.return_value = mock_diarization_result

        mock_record = MagicMock()
        mock_record.id = "uuid-456"

        with patch(
            "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.save",
            return_value=mock_record,
        ):
            use_case = ProcessAudioDiarizationPipelineUseCase(sqlite_memory)
            result = use_case.execute(
                source_type="upload",
                source="s3://test-bucket/audio.wav",
                recognize_voices=False,
            )

            assert result["storage_path"] == "processed/uuid-456/recognition"
        assert mock_storage.download_file.called

    @patch(
        "src.application.use_cases.process_audio_diarization_pipeline.StorageService"
    )
    @patch(
        "src.application.use_cases.process_audio_diarization_pipeline.YoutubeExtractor"
    )
    @patch("src.application.use_cases.process_audio_diarization_pipeline.AudioDiarizer")
    @patch("src.application.use_cases.process_audio_diarization_pipeline.VoiceDB")
    @patch("os.makedirs")
    @patch("os.replace")
    @patch("shutil.rmtree")
    @patch("os.path.exists", return_value=True)
    def test_execute_with_diarization_id(
        self,
        mock_exists,
        mock_rmtree,
        mock_replace,
        mock_makedirs,
        mock_voice_db_cls,
        mock_diarizer_cls,
        mock_extractor_cls,
        mock_storage_cls,
        sqlite_memory,
    ):
        mock_event_bus = MagicMock()
        mock_extractor = mock_extractor_cls.return_value
        mock_extractor.download_audio.return_value = "/tmp/audio.mp3"

        mock_diarizer = mock_diarizer_cls.return_value
        mock_diarization_result = MagicMock(spec=DiarizationResult)
        mock_diarizer.run.return_value = mock_diarization_result

        mock_record = MagicMock()
        mock_record.id = "existing-uuid"

        with (
            patch(
                "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.save",
                return_value=mock_record,
            ),
            patch(
                "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.update_status"
            ) as mock_update_status,
        ):
            use_case = ProcessAudioDiarizationPipelineUseCase(
                sqlite_memory, event_bus=mock_event_bus
            )
            use_case.execute(
                source_type="youtube",
                source="https://youtube.com/watch?v=test",
                diarization_id="existing-uuid",
                recognize_voices=False,
            )

            assert mock_event_bus.publish.called
            assert mock_update_status.called

    @patch(
        "src.application.use_cases.process_audio_diarization_pipeline.StorageService"
    )
    @patch(
        "src.application.use_cases.process_audio_diarization_pipeline.YoutubeExtractor"
    )
    @patch("src.application.use_cases.process_audio_diarization_pipeline.AudioDiarizer")
    @patch("src.application.use_cases.process_audio_diarization_pipeline.VoiceDB")
    @patch("os.makedirs")
    @patch("os.replace")
    @patch("shutil.rmtree")
    @patch("os.path.exists", return_value=True)
    def test_execute_metadata_error(
        self,
        mock_exists,
        mock_rmtree,
        mock_replace,
        mock_makedirs,
        mock_voice_db_cls,
        mock_diarizer_cls,
        mock_extractor_cls,
        mock_storage_cls,
        sqlite_memory,
    ):
        mock_extractor = mock_extractor_cls.return_value
        mock_extractor.download_audio.return_value = "/tmp/audio.mp3"
        mock_extractor.extract_metadata.side_effect = Exception("Metadata error")

        mock_diarizer = mock_diarizer_cls.return_value
        mock_diarization_result = MagicMock(spec=DiarizationResult)
        mock_diarizer.run.return_value = mock_diarization_result

        mock_record = MagicMock()
        mock_record.id = "uuid-789"

        with patch(
            "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.save",
            return_value=mock_record,
        ):
            use_case = ProcessAudioDiarizationPipelineUseCase(sqlite_memory)
            result = use_case.execute(
                source_type="youtube",
                source="https://youtube.com/watch?v=test",
                recognize_voices=False,
            )

            assert result["title"] == "audio"
            assert result["storage_path"] == "processed/uuid-789/recognition"
