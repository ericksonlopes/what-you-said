from unittest.mock import MagicMock, patch

import pytest

from src.application.dtos.commands.process_audio_command import ProcessAudioCommand
from src.application.workers import run_audio_diarization_dispatcher_worker


@pytest.mark.AudioDiarizationWorker
class TestAudioDiarizationWorker:
    @pytest.fixture
    def mock_app(self):
        app = MagicMock()
        app.state.task_queue = MagicMock()
        return app

    @pytest.fixture
    def mock_db_session(self):
        return MagicMock()

    def test_run_audio_diarization_dispatcher_worker_deduplication(self, mock_app, mock_db_session):
        # 1. Setup command
        cmd = ProcessAudioCommand(
            source_type="youtube",
            source="https://youtube.com/playlist?list=test",
            language="pt",
        )

        # 2. Mock individual video URLs from playlist
        video_urls = [
            "https://youtube.com/watch?v=v1",
            "https://youtube.com/watch?v=v2",
        ]

        # 3. Setup repository and mocks
        # One video exists, one does not
        existing_record = MagicMock(status="processing")

        with (
            patch("src.application.workers.registry.get", return_value=mock_app),
            patch("src.infrastructure.extractors.youtube_extractor.YoutubeExtractor") as mock_extractor_cls,
            patch(
                "src.infrastructure.connectors.connector_sql.Session",
                return_value=mock_db_session,
            ),
            patch("src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository") as mock_repo_cls,
        ):
            mock_extractor = mock_extractor_cls.return_value
            mock_extractor.extract_playlist_videos.return_value = video_urls

            mock_repo = mock_repo_cls.return_value
            # v1 exists, v2 does not
            mock_repo.get_by_external_source.side_effect = [existing_record, None]
            mock_repo.create_pending.return_value = MagicMock(id="new-record-id")

            # 4. Execute
            run_audio_diarization_dispatcher_worker(cmd)

            # 5. Assertions
            # Should check both URLs
            assert mock_repo.get_by_external_source.call_count == 2

            # Should only create pending for v2
            assert mock_repo.create_pending.call_count == 1
            mock_repo.create_pending.assert_called_once_with(
                name="https://youtube.com/watch?v=v2",
                source_type="youtube",
                external_source="https://youtube.com/watch?v=v2",
                language="pt",
                model_size=cmd.model_size,
                subject_id=None,
            )

            # Should only enqueue one task (for v2)
            assert mock_app.state.task_queue.enqueue.call_count == 1
            args, _ = mock_app.state.task_queue.enqueue.call_args
            single_cmd = args[1]
            assert single_cmd.source == "https://youtube.com/watch?v=v2"

    def test_run_audio_diarization_dispatcher_worker_retry_failed(self, mock_app, mock_db_session):
        # 1. Setup command
        cmd = ProcessAudioCommand(
            source_type="youtube",
            source="https://youtube.com/watch?v=v1",  # Works even if source is single but dispatcher is called
            language="pt",
        )

        # 2. Mock existing but FAILED record
        failed_record = MagicMock(status="failed")

        with (
            patch("src.application.workers.registry.get", return_value=mock_app),
            patch("src.infrastructure.extractors.youtube_extractor.YoutubeExtractor") as mock_extractor_cls,
            patch(
                "src.infrastructure.connectors.connector_sql.Session",
                return_value=mock_db_session,
            ),
            patch("src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository") as mock_repo_cls,
        ):
            mock_extractor = mock_extractor_cls.return_value
            # Mock playlist extraction to return one video
            mock_extractor.extract_playlist_videos.return_value = ["https://youtube.com/watch?v=v1"]

            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_external_source.return_value = failed_record
            mock_repo.create_pending.return_value = MagicMock(id="retry-id")

            # 4. Execute
            run_audio_diarization_dispatcher_worker(cmd)

            # 5. Assertions
            # Should NOT skip if status is failed
            assert mock_repo.create_pending.called
            assert mock_app.state.task_queue.enqueue.called
