from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app
from src.presentation.api.dependencies import get_job_service


@pytest.fixture
def mock_job_service():
    mock = MagicMock()
    app.dependency_overrides[get_job_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_job_service, None)


@pytest.mark.Dependencies
class TestJobRouter:
    def test_get_jobs_success(self, mock_job_service):
        client = TestClient(app)

        # Use SimpleNamespace to avoid MagicMock attributes being returned as Mocks
        mock_job = SimpleNamespace(
            id=uuid4(),
            status="finished",
            current_step=4,
            total_steps=4,
            status_message="Done",
            error_message=None,
            ingestion_type="youtube",
            source_title="Test Title",
            content_source_id=uuid4(),
            chunks_count=5,
            created_at=datetime.now(timezone.utc),
        )

        mock_job_service.list_jobs.return_value = {
            "jobs": [mock_job],
            "total": 1,
            "stats": {"total": 1, "processing": 0, "completed": 1, "failed": 0},
        }

        response = client.get("/rest/jobs")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == str(mock_job.id)
        assert data["items"][0]["status"] == "finished"
        assert data["items"][0]["source_title"] == "Test Title"
        assert data["total"] == 1

    def test_get_jobs_error(self, mock_job_service):
        client = TestClient(app)
        mock_job_service.list_jobs.side_effect = Exception("DB error")

        response = client.get("/rest/jobs")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"
