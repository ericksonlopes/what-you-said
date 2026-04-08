import asyncio
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from src.application.dtos.commands.ingest_file_command import IngestFileCommand
from src.application.dtos.commands.ingest_youtube_command import IngestYoutubeCommand
from src.application.dtos.enums.youtube_data_type import YoutubeDataType
from src.application.service_registry import registry
from src.application.workers import (
    run_file_ingestion_worker,
    run_web_ingestion_worker,
    run_youtube_ingestion_worker,
)


@pytest.mark.Workers
class TestWorkers:
    @pytest.fixture(autouse=True)
    def setup_registry(self):
        # Clear and setup registry
        registry._services = {}
        mock_app = MagicMock()
        registry.register("app", mock_app)
        yield
        registry._services = {}

    def test_run_file_ingestion_worker_success(self):
        with (
            patch("src.presentation.api.dependencies.resolve_ingestion_context") as mock_ctx,
            patch("src.presentation.api.dependencies.resolve_vector_repository"),
            patch("src.presentation.api.dependencies.resolve_rerank_service"),
            patch("src.infrastructure.services.chunk_vector_service.ChunkVectorService"),
            patch("src.application.use_cases.file_ingestion_use_case.FileIngestionUseCase") as mock_use_case_cls,
        ):
            mock_use_case = MagicMock()
            mock_use_case_cls.return_value = mock_use_case
            mock_ctx.return_value = MagicMock()

            cmd = IngestFileCommand(file_path="test.pdf", file_name="test.pdf", subject_name="test")
            run_file_ingestion_worker(cmd)
            mock_use_case.execute.assert_called_once_with(cmd)

    def test_run_file_ingestion_worker_no_app(self):
        registry._services = {}  # Remove app
        cmd = IngestFileCommand(file_path="test.pdf", file_name="test.pdf", subject_name="test")
        with patch("src.application.workers.logger") as mock_logger:
            run_file_ingestion_worker(cmd)
            mock_logger.error.assert_called_once()

    def test_run_file_ingestion_worker_exception(self):
        with patch("src.presentation.api.dependencies.resolve_ingestion_context") as mock_ctx:
            mock_ctx.side_effect = Exception("Test error")
            cmd = IngestFileCommand(file_path="test.pdf", file_name="test.pdf", subject_name="test")
            with patch("src.application.workers.logger") as mock_logger:
                run_file_ingestion_worker(cmd)
                mock_logger.error.assert_called_once()

    def test_run_youtube_ingestion_worker_success(self):
        with (
            patch("src.presentation.api.dependencies.resolve_ingestion_context") as mock_ctx,
            patch("src.presentation.api.dependencies.resolve_vector_repository"),
            patch("src.infrastructure.services.youtube_vector_service.YouTubeVectorService"),
            patch("src.application.use_cases.youtube_ingestion_use_case.YoutubeIngestionUseCase") as mock_use_case_cls,
        ):
            mock_use_case = MagicMock()
            mock_use_case_cls.return_value = mock_use_case
            mock_ctx.return_value = MagicMock()

            cmd = IngestYoutubeCommand(
                video_url="https://youtube.com/watch?v=123",
                subject_name="test",
                data_type=YoutubeDataType.VIDEO,
            )
            run_youtube_ingestion_worker(cmd)
            mock_use_case.execute.assert_called_once_with(cmd)

    def test_run_youtube_ingestion_worker_no_app(self):
        registry._services = {}  # Remove app
        cmd = IngestYoutubeCommand(
            video_url="https://youtube.com/watch?v=123",
            subject_name="test",
            data_type=YoutubeDataType.VIDEO,
        )
        run_youtube_ingestion_worker(cmd)
        # Should return silently

    def test_run_youtube_ingestion_worker_exception(self):
        with patch("src.presentation.api.dependencies.resolve_ingestion_context") as mock_ctx:
            mock_ctx.side_effect = Exception("Test error")
            cmd = IngestYoutubeCommand(
                video_url="https://youtube.com/watch?v=123",
                subject_name="test",
                data_type=YoutubeDataType.VIDEO,
            )
            with patch("src.application.workers.logger") as mock_logger:
                run_youtube_ingestion_worker(cmd)
                mock_logger.error.assert_called_once()

    def test_run_web_ingestion_worker_success(self):
        with (
            patch("src.presentation.api.dependencies.resolve_ingestion_context") as mock_ctx,
            patch("src.presentation.api.dependencies.resolve_vector_repository"),
            patch("src.presentation.api.dependencies.resolve_rerank_service"),
            patch("src.infrastructure.services.chunk_vector_service.ChunkVectorService"),
            patch("src.presentation.api.dependencies.get_web_extractor"),
            patch("src.application.use_cases.web_scraping_use_case.WebScrapingUseCase") as mock_use_case_cls,
            patch("asyncio.run") as mock_asyncio_run,
        ):
            mock_use_case = MagicMock()
            mock_use_case.execute = AsyncMock()
            mock_use_case_cls.return_value = mock_use_case
            mock_ctx.return_value = MagicMock()

            # Capture the coroutine and run it in a new loop to avoid RuntimeError
            def side_effect(coro):
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()

            mock_asyncio_run.side_effect = side_effect

            cmd = MagicMock()
            cmd.ingestion_job_id = "test-job"
            run_web_ingestion_worker(cmd)
            mock_use_case.execute.assert_called_once_with(cmd)

    def test_run_web_ingestion_worker_no_app(self):
        registry._services = {}  # Remove app
        cmd = MagicMock()
        cmd.ingestion_job_id = "test-job"
        run_web_ingestion_worker(cmd)
        # Should return silently

    def test_run_web_ingestion_worker_exception(self):
        with (
            patch("src.presentation.api.dependencies.resolve_ingestion_context") as mock_ctx,
            patch("asyncio.run") as mock_asyncio_run,
        ):
            mock_ctx.side_effect = Exception("Test error")

            def side_effect(coro):
                loop = asyncio.new_event_loop()
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()

            mock_asyncio_run.side_effect = side_effect

            cmd = MagicMock()
            cmd.ingestion_job_id = "test-job"
            with patch("logging.getLogger") as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger
                run_web_ingestion_worker(cmd)
                mock_logger.error.assert_called_once()

    def test_run_diarization_ingestion_worker_success(self):
        from uuid import uuid4

        from src.application.dtos.commands.ingest_diarization_command import (
            IngestDiarizationCommand,
        )
        from src.application.workers import run_diarization_ingestion_worker

        with (
            patch("src.presentation.api.dependencies.resolve_ingestion_context") as mock_ctx,
            patch("src.presentation.api.dependencies.resolve_vector_repository"),
            patch("src.presentation.api.dependencies.resolve_rerank_service"),
            patch("src.infrastructure.services.chunk_vector_service.ChunkVectorService"),
            patch("src.infrastructure.connectors.connector_sql.Session") as mock_session_cls,
            patch("src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository"),
            patch(
                "src.application.use_cases.diarization_ingestion_use_case.DiarizationIngestionUseCase"
            ) as mock_use_case_cls,
        ):
            mock_use_case = MagicMock()
            mock_use_case_cls.return_value = mock_use_case
            mock_ctx.return_value = MagicMock()
            mock_session_cls.return_value = MagicMock()

            cmd = IngestDiarizationCommand(
                diarization_id=uuid4(),
                subject_id=uuid4(),
            )
            run_diarization_ingestion_worker(cmd)
            mock_use_case.execute.assert_called_once_with(cmd)

    def test_run_diarization_ingestion_worker_no_app(self):
        from src.application.workers import run_diarization_ingestion_worker

        registry._services = {}
        cmd = MagicMock()
        run_diarization_ingestion_worker(cmd)
        # Should return early

    def test_run_diarization_ingestion_worker_exception(self):
        from src.application.workers import run_diarization_ingestion_worker

        with patch("src.presentation.api.dependencies.resolve_ingestion_context") as mock_ctx:
            mock_ctx.side_effect = Exception("Test error")
            cmd = MagicMock()
            with patch("src.application.workers.logger") as mock_logger:
                run_diarization_ingestion_worker(cmd)
                mock_logger.error.assert_called_once()

    def test_audio_diarization_subprocess_success(self):
        from src.application.workers import _audio_diarization_subprocess

        with (
            patch("src.infrastructure.connectors.connector_sql.Session") as mock_session_cls,
            patch("src.infrastructure.services.redis_event_bus.RedisEventBus"),
            patch(
                "src.application.use_cases.process_audio_diarization_pipeline.ProcessAudioDiarizationPipelineUseCase"
            ) as mock_use_case_cls,
        ):
            mock_use_case = MagicMock()
            mock_use_case_cls.return_value = mock_use_case
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session

            cmd_dict = {
                "source_type": "youtube",
                "source": "url",
                "language": "pt",
                "num_speakers": None,
                "min_speakers": None,
                "max_speakers": None,
                "model_size": "base",
                "recognize_voices": True,
                "diarization_id": "test-id",
            }
            _audio_diarization_subprocess(cmd_dict)
            mock_use_case.execute.assert_called_once()

    def test_run_audio_diarization_worker_success(self):
        from src.application.dtos.commands.process_audio_command import (
            ProcessAudioCommand,
        )
        from src.application.workers import run_audio_diarization_worker

        with (
            patch("multiprocessing.get_context") as mock_get_ctx,
        ):
            mock_ctx = MagicMock()
            mock_get_ctx.return_value = mock_ctx
            mock_process = MagicMock()
            mock_ctx.Process.return_value = mock_process
            mock_process.exitcode = 0

            cmd = ProcessAudioCommand(source_type="youtube", source="url")
            run_audio_diarization_worker(cmd)

            mock_ctx.Process.assert_called_once()
            mock_process.start.assert_called_once()
            mock_process.join.assert_called_once()

    def test_run_audio_diarization_worker_failure(self):
        from src.application.dtos.commands.process_audio_command import (
            ProcessAudioCommand,
        )
        from src.application.workers import run_audio_diarization_worker

        with (
            patch("multiprocessing.get_context") as mock_get_ctx,
            patch("src.infrastructure.connectors.connector_sql.Session") as mock_session_factory,
            patch("src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository") as mock_repo_cls,
            patch("src.infrastructure.services.redis_event_bus.RedisEventBus"),
        ):
            mock_ctx = MagicMock()
            mock_get_ctx.return_value = mock_ctx
            mock_process = MagicMock()
            mock_ctx.Process.return_value = mock_process
            mock_process.exitcode = 1

            mock_session = MagicMock()
            mock_session_factory.return_value = mock_session
            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo

            cmd = ProcessAudioCommand(source_type="youtube", source="url", diarization_id="test-id")
            run_audio_diarization_worker(cmd)

            mock_repo.update_status.assert_called_with("test-id", "failed", error_message=ANY, status_message=ANY)
