import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from main import app
from src.presentation.api.dependencies import get_ks_service, get_ks_use_case

client = TestClient(app)


@pytest.mark.Dependencies
class TestSubjectRouter:
    @pytest.fixture
    def mock_ks_service(self):
        mock = MagicMock()
        app.dependency_overrides[get_ks_service] = lambda: mock
        yield mock
        app.dependency_overrides.pop(get_ks_service, None)

    @pytest.fixture
    def mock_ks_use_case(self):
        mock = MagicMock()
        app.dependency_overrides[get_ks_use_case] = lambda: mock
        yield mock
        app.dependency_overrides.pop(get_ks_use_case, None)

    def test_create_subject_success(self, mock_ks_service):
        mock_ks_service.create_subject.return_value = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "test",
            "description": "desc",
            "icon": "icon",
        }

        response = client.post(
            "/rest/subjects", json={"name": "test", "description": "desc"}
        )

        assert response.status_code == 201
        mock_ks_service.create_subject.assert_called_once()

    def test_create_subject_error(self, mock_ks_service):
        mock_ks_service.create_subject.side_effect = Exception("Error")

        response = client.post("/rest/subjects", json={"name": "test"})

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    def test_get_subjects_success(self, mock_ks_service):
        mock_ks_service.list_subjects.return_value = []

        response = client.get("/rest/subjects")

        assert response.status_code == 200
        assert response.json() == []
        mock_ks_service.list_subjects.assert_called_once()

    def test_get_subjects_error(self, mock_ks_service):
        mock_ks_service.list_subjects.side_effect = Exception("Error")

        response = client.get("/rest/subjects")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    def test_delete_subject_success(self, mock_ks_use_case):
        mock_ks_use_case.delete_knowledge.return_value = True

        response = client.delete("/rest/subjects/123e4567-e89b-12d3-a456-426614174000")

        assert response.status_code == 204
        mock_ks_use_case.delete_knowledge.assert_called_once()

    def test_delete_subject_not_found(self, mock_ks_use_case):
        mock_ks_use_case.delete_knowledge.return_value = False

        response = client.delete("/rest/subjects/123e4567-e89b-12d3-a456-426614174000")

        assert response.status_code == 404
        assert response.json()["detail"] == "Subject not found"

    def test_delete_subject_error(self, mock_ks_use_case):
        mock_ks_use_case.delete_knowledge.side_effect = Exception("Error")

        response = client.delete("/rest/subjects/123e4567-e89b-12d3-a456-426614174000")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"
