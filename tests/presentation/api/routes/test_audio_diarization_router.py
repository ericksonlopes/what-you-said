from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from src.infrastructure.repositories.sql.models.diarization_record import (
    DiarizationRecord,
)
from src.presentation.api.dependencies import (
    get_db,
    get_task_queue_service,
    get_identify_speakers_use_case,
    get_retrieve_history_use_case,
    get_generate_speaker_url_use_case,
    get_list_s3_files_use_case
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

    def test_update_diarization_segments_success(self, mock_db):
        app.dependency_overrides[get_db] = lambda: mock_db

        record_mock = MagicMock(spec=DiarizationRecord)
        record_mock.id = "123"

        with patch(
            "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.get_by_id",
            return_value=record_mock,
        ):
            response = client.patch(
                "/rest/audio/123", json={"segments": [{"text": "hello"}]}
            )

            assert response.status_code == 200
            assert response.json()["status"] == "success"
            assert record_mock.status == "completed"

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

        with patch(
            "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.create_pending",
            return_value=record_mock,
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
                "src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.get_by_id") as mock_get:
            mock_get.side_effect = Exception("DB Fail")
            response = client.patch("/rest/audio/123", json={"segments": []})
            assert response.status_code == 500
        app.dependency_overrides.clear()

    def test_identify_speakers_value_error_400(self, mock_db):
        app.dependency_overrides[get_identify_speakers_use_case] = lambda: MagicMock(
            execute=MagicMock(side_effect=ValueError("invalid")))
        response = client.post("/rest/audio/123/recognize")
        assert response.status_code == 400
        app.dependency_overrides.clear()

    def test_identify_speakers_exception_500(self, mock_db):
        app.dependency_overrides[get_identify_speakers_use_case] = lambda: MagicMock(
            execute=MagicMock(side_effect=Exception("crash")))
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
            execute=MagicMock(side_effect=ValueError("not found")))
        response = client.get("/rest/audio/123/s3/list")
        assert response.status_code == 404
        app.dependency_overrides.clear()

    def test_generate_signed_url_error_500(self, mock_db):
        app.dependency_overrides[get_generate_speaker_url_use_case] = lambda: MagicMock(
            execute=MagicMock(side_effect=Exception("s3 error")))
        response = client.get("/rest/audio/123/audio/S1")
        assert response.status_code == 500
        app.dependency_overrides.clear()

    def test_delete_record_not_found(self, mock_db):
        app.dependency_overrides[get_db] = lambda: mock_db
        with patch("src.infrastructure.repositories.sql.diarization_repository.DiarizationRepository.delete",
                   return_value=False):
            response = client.delete("/rest/audio/nonexistent")
            assert response.status_code == 404
        app.dependency_overrides.clear()
