from unittest.mock import MagicMock, patch, AsyncMock
import pytest
import asyncio
from src.application.service_registry import registry
from src.application.workers import (
    run_file_ingestion_worker,
    run_youtube_ingestion_worker,
    run_web_ingestion_worker,
)
from src.application.dtos.commands.ingest_file_command import IngestFileCommand
from src.application.dtos.commands.ingest_youtube_command import IngestYoutubeCommand
from src.application.dtos.enums.youtube_data_type import YoutubeDataType


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
            patch(
                "src.presentation.api.dependencies.resolve_ingestion_context"
            ) as mock_ctx,
            patch(
                "src.presentation.api.dependencies.resolve_vector_repository"
            ),
            patch(
                "src.presentation.api.dependencies.resolve_rerank_service"
            ),
            patch(
                "src.infrastructure.services.chunk_vector_service.ChunkVectorService"
            ),
            patch(
                "src.application.use_cases.file_ingestion_use_case.FileIngestionUseCase"
            ) as mock_use_case_cls,
        ):
            mock_use_case = MagicMock()
            mock_use_case_cls.return_value = mock_use_case
            mock_ctx.return_value = MagicMock()

            cmd = IngestFileCommand(
                file_path="test.pdf", file_name="test.pdf", subject_name="test"
            )
            run_file_ingestion_worker(cmd)
            mock_use_case.execute.assert_called_once_with(cmd)

    def test_run_file_ingestion_worker_no_app(self):
        registry._services = {}  # Remove app
        cmd = IngestFileCommand(
            file_path="test.pdf", file_name="test.pdf", subject_name="test"
        )
        with patch("src.application.workers.logger") as mock_logger:
            run_file_ingestion_worker(cmd)
            mock_logger.error.assert_called_once()

    def test_run_file_ingestion_worker_exception(self):
        with patch(
            "src.presentation.api.dependencies.resolve_ingestion_context"
        ) as mock_ctx:
            mock_ctx.side_effect = Exception("Test error")
            cmd = IngestFileCommand(
                file_path="test.pdf", file_name="test.pdf", subject_name="test"
            )
            with patch("src.application.workers.logger") as mock_logger:
                run_file_ingestion_worker(cmd)
                mock_logger.error.assert_called_once()

    def test_run_youtube_ingestion_worker_success(self):
        with (
            patch(
                "src.presentation.api.dependencies.resolve_ingestion_context"
            ) as mock_ctx,
            patch(
                "src.presentation.api.dependencies.resolve_vector_repository"
            ),
            patch(
                "src.infrastructure.services.youtube_vector_service.YouTubeVectorService"
            ),
            patch(
                "src.application.use_cases.youtube_ingestion_use_case.YoutubeIngestionUseCase"
            ) as mock_use_case_cls,
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
        with patch(
            "src.presentation.api.dependencies.resolve_ingestion_context"
        ) as mock_ctx:
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
            patch(
                "src.presentation.api.dependencies.resolve_ingestion_context"
            ) as mock_ctx,
            patch(
                "src.presentation.api.dependencies.resolve_vector_repository"
            ),
            patch(
                "src.presentation.api.dependencies.resolve_rerank_service"
            ),
            patch(
                "src.infrastructure.services.chunk_vector_service.ChunkVectorService"
            ),
            patch(
                "src.presentation.api.dependencies.get_web_extractor"
            ),
            patch(
                "src.application.use_cases.web_scraping_use_case.WebScrapingUseCase"
            ) as mock_use_case_cls,
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
            patch(
                "src.presentation.api.dependencies.resolve_ingestion_context"
            ) as mock_ctx,
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
