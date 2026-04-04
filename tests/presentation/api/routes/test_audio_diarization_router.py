import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app
from src.presentation.api.dependencies import get_db, get_task_queue_service
from src.infrastructure.repositories.sql.models.diarization_record import (
    DiarizationRecord,
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

        with patch(
            "src.application.use_cases.identify_speakers_in_processed_audio.IdentifySpeakersInProcessedAudioUseCase.execute"
        ) as mock_exec:
            mock_exec.return_value = {"mapping": {"S1": "User"}}
            response = client.post("/rest/audio/123/recognize")

            assert response.status_code == 200
            assert response.json()["mapping"]["S1"] == "User"

        app.dependency_overrides.clear()

    def test_retrieve_history(self, mock_db):
        app.dependency_overrides[get_db] = lambda: mock_db

        with patch(
            "src.application.use_cases.retrieve_processed_audio_history.RetrieveProcessedAudioHistoryUseCase.execute"
        ) as mock_exec:
            mock_exec.return_value = [{"id": "1", "title": "Test"}]
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
