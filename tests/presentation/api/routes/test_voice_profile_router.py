import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from main import app
from src.presentation.api.dependencies import (
    get_db,
    get_register_voice_profile_use_case,
    get_train_voice_from_speaker_use_case,
    get_list_voice_profiles_use_case,
    get_delete_voice_profile_use_case,
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
        app.dependency_overrides[get_db] = lambda: MagicMock()
        mock_use_case = MagicMock()
        app.dependency_overrides[get_train_voice_from_speaker_use_case] = lambda: (
            mock_use_case
        )

        mock_use_case.execute.return_value = "v-456"
        payload = {
            "diarization_id": "d-1",
            "speaker_label": "SPEAKER_00",
            "name": "Bob",
        }
        response = client.post("/rest/voices/train-from-speaker", json=payload)
        assert response.status_code == 200
        assert response.json()["voice_id"] == "v-456"

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
