from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from src.infrastructure.repositories.sql.models.diarization_record import (
    DiarizationRecord,
)
from src.presentation.api.dependencies import (
    get_db,
    get_generate_speaker_url_use_case,
    get_identify_speakers_use_case,
    get_list_s3_files_use_case,
    get_retrieve_history_use_case,
    get_task_queue_service,
)

client = TestClient(app)


@pytest.mark.AudioDiarizationRouter
class TestAudioDiarizationRouter:
    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def mock_task_queue(self):
        return MagicMock()

    def test_update_diarization_segments_success(self, mock_db, mock_task_queue):
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_task_queue_service] = lambda: mock_task_queue

        record_mock = MagicMock(spec=DiarizationRecord)
        record_mock.id = "daced256-b5b0-4916-980e-3428a87eb737"
        record_mock.status = "pending"

        # Mock ContentSource to cover the additional logic
        mock_cs = MagicMock()
        mock_cs.id = "cs-123"
        mock_cs.subject_id = "subj-123"
        mock_cs.title = "Test Audio"
        mock_cs.language = "pt"
        mock_cs.source_type = "youtube"
        mock_cs.external_source = "vid-123"
        mock_cs.source_metadata = {"diarization_id": record_mock.id}

        with (
            patch(
                "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.get_by_id",
                return_value=record_mock,
            ),
            patch(
                "src.infrastructure.repositories.sql.content_source_repository.ContentSourceSQLRepository"
            ) as mock_cs_repo_cls,
        ):
            mock_cs_repo = mock_cs_repo_cls.return_value
            mock_cs_repo.get_by_diarization_id.return_value = mock_cs

            response = client.patch(
                f"/rest/audio/{record_mock.id}", json={"segments": [{"text": "hello"}]}
            )

            assert response.status_code == 200
            assert response.json()["status"] == "success"
            assert record_mock.status == "completed"

            # Verify ingestion was triggered
            assert mock_task_queue.enqueue.called

        app.dependency_overrides.clear()

    def test_update_diarization_segments_not_found(self, mock_db):
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch(
            "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.get_by_id",
            return_value=None,
        ):
            response = client.patch("/rest/audio/nonexistent", json={"segments": []})
            assert response.status_code == 404

        app.dependency_overrides.clear()

    def test_start_audio_processing_pipeline(self, mock_db, mock_task_queue):
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_task_queue_service] = lambda: mock_task_queue

        record_mock = MagicMock(id="new-uuid")

        with (
            patch(
                "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.get_by_external_source",
                return_value=None,
            ),
            patch(
                "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.create_pending",
                return_value=record_mock,
            ),
        ):
            payload = {
                "source_type": "youtube",
                "source": "https://youtube.com/watch?v=test",
                "language": "pt",
            }
            response = client.post("/rest/audio", json=payload)

            assert response.status_code == 200
            assert response.json()["id"] == "new-uuid"
            assert mock_task_queue.enqueue.called

        app.dependency_overrides.clear()

    def test_start_audio_processing_pipeline_duplicate(self, mock_db, mock_task_queue):
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_task_queue_service] = lambda: mock_task_queue

        existing_record = MagicMock(id="existing-uuid", status="processing")

        with (
            patch(
                "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.get_by_external_source",
                return_value=existing_record,
            ),
            patch(
                "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.create_pending"
            ) as mock_create,
        ):
            payload = {
                "source_type": "youtube",
                "source": "https://youtube.com/watch?v=test",
                "language": "pt",
            }
            response = client.post("/rest/audio", json=payload)

            assert response.status_code == 200
            assert response.json()["id"] == "existing-uuid"
            assert "already processed" in response.json()["message"]
            assert not mock_create.called
            assert not mock_task_queue.enqueue.called

        app.dependency_overrides.clear()

        app.dependency_overrides.clear()

    def test_start_audio_processing_pipeline_with_subject(
        self, mock_db, mock_task_queue
    ):
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_task_queue_service] = lambda: mock_task_queue
        record_mock = MagicMock(id="new-uuid")

        with (
            patch(
                "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.get_by_external_source",
                return_value=None,
            ),
            patch(
                "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.create_pending",
                return_value=record_mock,
            ),
        ):
            payload = {
                "source_type": "youtube",
                "source": "https://youtube.com/watch?v=test",
                "subject_id": "893c5240-f1c5-412e-9d6e-8d54c1e679a2",
            }
            response = client.post("/rest/audio", json=payload)
            assert response.status_code == 200
            assert response.json()["id"] == "new-uuid"

        app.dependency_overrides.clear()

    def test_start_audio_processing_pipeline_failed_retry(
        self, mock_db, mock_task_queue
    ):
        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_task_queue_service] = lambda: mock_task_queue

        # Existing but failed
        existing_record = MagicMock(id="old-uuid", status="failed")
        new_record = MagicMock(id="new-uuid")

        with (
            patch(
                "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.get_by_external_source",
                return_value=existing_record,
            ),
            patch(
                "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.create_pending",
                return_value=new_record,
            ),
        ):
            payload = {
                "source_type": "youtube",
                "source": "https://youtube.com/watch?v=test",
            }
            response = client.post("/rest/audio", json=payload)
            assert response.status_code == 200
            assert response.json()["id"] == "new-uuid"
            assert mock_task_queue.enqueue.called

        app.dependency_overrides.clear()

    def test_identify_speakers_existing(self, mock_db):
        app.dependency_overrides[get_db] = lambda: mock_db
        mock_use_case = MagicMock()
        app.dependency_overrides[get_identify_speakers_use_case] = lambda: mock_use_case

        mock_use_case.execute.return_value = {"mapping": {"S1": "User"}}
        response = client.post("/rest/audio/123/recognize")

        assert response.status_code == 200
        assert response.json()["mapping"]["S1"] == "User"

        app.dependency_overrides.clear()

    def test_retrieve_history(self, mock_db):
        app.dependency_overrides[get_db] = lambda: mock_db
        mock_use_case = MagicMock()
        app.dependency_overrides[get_retrieve_history_use_case] = lambda: mock_use_case

        mock_use_case.execute.return_value = [{"id": "1", "title": "Test"}]
        response = client.get("/rest/audio?limit=5")

        assert response.status_code == 200
        assert len(response.json()) == 1

        app.dependency_overrides.clear()

    def test_delete_record(self, mock_db):
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch(
            "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.delete",
            return_value=True,
        ):
            response = client.delete("/rest/audio/123")
            assert response.status_code == 200
            assert response.json()["status"] == "success"

        app.dependency_overrides.clear()

    def test_update_diarization_segments_db_error(self, mock_db):
        app.dependency_overrides[get_db] = lambda: mock_db
        with patch(
            "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.get_by_id"
        ) as mock_get:
            mock_get.side_effect = Exception("DB Fail")
            response = client.patch("/rest/audio/123", json={"segments": []})
            assert response.status_code == 500
        app.dependency_overrides.clear()

    def test_identify_speakers_value_error_400(self, mock_db):
        app.dependency_overrides[get_identify_speakers_use_case] = lambda: MagicMock(
            execute=MagicMock(side_effect=ValueError("invalid"))
        )
        response = client.post("/rest/audio/123/recognize")
        assert response.status_code == 400
        app.dependency_overrides.clear()

    def test_identify_speakers_exception_500(self, mock_db):
        app.dependency_overrides[get_identify_speakers_use_case] = lambda: MagicMock(
            execute=MagicMock(side_effect=Exception("crash"))
        )
        response = client.post("/rest/audio/123/recognize")
        assert response.status_code == 500
        app.dependency_overrides.clear()

    def test_list_s3_files_success(self, mock_db):
        mock_use_case = MagicMock(execute=MagicMock(return_value=[{"key": "k"}]))
        app.dependency_overrides[get_list_s3_files_use_case] = lambda: mock_use_case
        response = client.get("/rest/audio/123/s3/list")
        assert response.status_code == 200
        assert response.json()[0]["key"] == "k"
        app.dependency_overrides.clear()

    def test_list_s3_files_error_404(self, mock_db):
        app.dependency_overrides[get_list_s3_files_use_case] = lambda: MagicMock(
            execute=MagicMock(side_effect=ValueError("not found"))
        )
        response = client.get("/rest/audio/123/s3/list")
        assert response.status_code == 404
        app.dependency_overrides.clear()

    def test_generate_signed_url_error_500(self, mock_db):
        app.dependency_overrides[get_generate_speaker_url_use_case] = lambda: MagicMock(
            execute=MagicMock(side_effect=Exception("s3 error"))
        )
        response = client.get("/rest/audio/123/audio/S1")
        assert response.status_code == 500
        app.dependency_overrides.clear()

    def test_delete_record_not_found(self, mock_db):
        app.dependency_overrides[get_db] = lambda: mock_db
        with patch(
            "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.delete",
            return_value=False,
        ):
            response = client.delete("/rest/audio/nonexistent")
            assert response.status_code == 404
        app.dependency_overrides.clear()
