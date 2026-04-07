from unittest.mock import MagicMock, mock_open, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from src.presentation.api.dependencies import (
    get_db,
    get_delete_voice_profile_use_case,
    get_diarization_repo,
    get_event_bus,
    get_list_voice_profiles_use_case,
    get_register_voice_profile_use_case,
    get_task_queue_service,
)

client = TestClient(app)


@pytest.mark.VoiceProfileRouter
class TestVoiceProfileRouter:
    def test_register_voice_profile_success(self):
        app.dependency_overrides[get_db] = lambda: MagicMock()
        mock_use_case = MagicMock()
        app.dependency_overrides[get_register_voice_profile_use_case] = lambda: (
            mock_use_case
        )

        mock_use_case.execute.return_value = "v-123"
        response = client.post(
            "/rest/voices", json={"name": "Alice", "audio_path": "s3://path"}
        )
        assert response.status_code == 200
        assert response.json()["voice_id"] == "v-123"

        app.dependency_overrides.clear()

    def test_train_from_speaker_success(self):
        # 1. Mock dependencies
        app.dependency_overrides[get_db] = lambda: MagicMock()
        mock_task_queue = MagicMock()
        app.dependency_overrides[get_task_queue_service] = lambda: mock_task_queue

        mock_repo = MagicMock()
        app.dependency_overrides[get_diarization_repo] = lambda: mock_repo
        mock_repo.get_by_id.return_value = MagicMock(id="d-1")

        mock_event_bus = MagicMock()
        app.dependency_overrides[get_event_bus] = lambda: mock_event_bus

        # 2. Execute request
        payload = {
            "diarization_id": "d-1",
            "speaker_label": "SPEAKER_00",
            "name": "Bob",
        }
        response = client.post("/rest/voices/train-from-speaker", json=payload)

        # 3. Assert status and body
        assert response.status_code == 202
        assert "Treinamento de voz iniciado" in response.json()["message"]
        assert response.json()["name"] == "Bob"

        # 4. Verify queue was called
        assert mock_task_queue.enqueue.called

        app.dependency_overrides.clear()

        app.dependency_overrides.clear()

    def test_list_voices(self):
        app.dependency_overrides[get_db] = lambda: MagicMock()
        mock_use_case = MagicMock()
        app.dependency_overrides[get_list_voice_profiles_use_case] = lambda: (
            mock_use_case
        )

        mock_use_case.execute.return_value = [{"name": "Alice"}]
        response = client.get("/rest/voices")
        assert response.status_code == 200
        assert len(response.json()) == 1

        app.dependency_overrides.clear()

    def test_delete_voice_success(self):
        app.dependency_overrides[get_db] = lambda: MagicMock()
        mock_use_case = MagicMock()
        app.dependency_overrides[get_delete_voice_profile_use_case] = lambda: (
            mock_use_case
        )

        mock_use_case.execute.return_value = None
        response = client.delete("/rest/voices/Alice")
        assert response.status_code == 200
        assert "successfully removed" in response.json()["message"]

        app.dependency_overrides.clear()

    def test_delete_voice_not_found(self):
        app.dependency_overrides[get_db] = lambda: MagicMock()
        mock_use_case = MagicMock()
        app.dependency_overrides[get_delete_voice_profile_use_case] = lambda: (
            mock_use_case
        )

        mock_use_case.execute.side_effect = KeyError("not found")
        response = client.delete("/rest/voices/Unknown")
        assert response.status_code == 404

        app.dependency_overrides.clear()

    def test_upload_voice_profile_success(self):
        app.dependency_overrides[get_db] = lambda: MagicMock()
        mock_use_case = MagicMock()
        app.dependency_overrides[get_register_voice_profile_use_case] = lambda: (
            mock_use_case
        )

        mock_use_case.execute.return_value = "v-123"

        from io import BytesIO

        file_content = b"fake audio content"
        files = {"file": ("test.wav", BytesIO(file_content), "audio/wav")}
        data = {"name": "Alice", "force": "false"}

        with (
            patch("shutil.copyfileobj"),
            patch("tempfile.mkdtemp", return_value="/tmp/test"),
            patch("os.path.exists", return_value=True),
            patch("os.remove"),
            patch("os.rmdir"),
            patch("builtins.open", mock_open()),
        ):
            response = client.post("/rest/voices/upload", data=data, files=files)

        assert response.status_code == 200
        assert response.json()["voice_id"] == "v-123"

        app.dependency_overrides.clear()

    def test_get_voice_audio_url_success(self):
        # Patch the StorageService class inside the router module
        with patch(
            "src.presentation.api.routes.voice_profile_management_router.StorageService"
        ) as mock_storage_cls:
            mock_storage = mock_storage_cls.return_value
            mock_storage.get_presigned_url.return_value = "http://presigned-url"

            response = client.get("/rest/voices/audios/path/to/voice.wav")

            assert response.status_code == 200
            assert response.json()["url"] == "http://presigned-url"
