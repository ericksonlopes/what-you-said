import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from main import app
from src.presentation.api.dependencies import get_file_ingestion_use_case
from uuid import uuid4


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_file_use_case():
    mock = MagicMock()
    app.dependency_overrides[get_file_ingestion_use_case] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_file_ingestion_use_case, None)


@pytest.mark.Dependencies
class TestIngestRouterFile:
    def test_ingest_file_success(self, client, mock_file_use_case):
        # Setup mock
        mock_file_use_case.execute.return_value = {"job_id": str(uuid4())}

        subject_id = str(uuid4())
        file_content = b"test content"
        files = {"file": ("test.txt", file_content, "text/plain")}
        data = {"subject_id": subject_id, "title": "Test File", "language": "en"}

        response = client.post("/rest/ingest/file", files=files, data=data)

        assert response.status_code == 200
        assert (
            response.json()["message"]
            == "File upload successful, ingestion started in background."
        )
        assert response.json()["file_name"] == "test.txt"

    def test_ingest_file_invalid_uuid(self, client, mock_file_use_case):
        files = {"file": ("test.txt", b"content", "text/plain")}
        data = {"subject_id": "not-a-uuid"}

        response = client.post("/rest/ingest/file", files=files, data=data)
        assert response.status_code == 400
        assert "Invalid subject_id format" in response.json()["detail"]

    def test_ingest_file_missing_file(self, client):
        response = client.post("/rest/ingest/file", data={"subject_name": "test"})
        assert (
            response.status_code == 422
        )  # FastAPI validation error for missing required File
