from unittest.mock import MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from main import app
from src.application.dtos.results.ingest_youtube_result import IngestYoutubeResult
from src.presentation.api.dependencies import get_ingest_youtube_use_case

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_app_state():
    app.state.task_queue = MagicMock()
    app.state.event_bus = MagicMock()
    yield
    # No need to cleanup state in simple tests, but could if needed


@pytest.fixture
def mock_use_case():
    mock = MagicMock()
    app.dependency_overrides[get_ingest_youtube_use_case] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_ingest_youtube_use_case, None)


def test_ingest_youtube_success(mock_use_case):
    mock_use_case.execute.return_value = IngestYoutubeResult(
        skipped=False,
        reason=None,
        source_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
        created_chunks=10,
        vector_ids=["vid1", "vid2"],
        video_results=[],
    )

    response = client.post(
        "/rest/ingest/youtube", json={"video_url": "https://youtube.com/watch?v=123"}
    )

    assert response.status_code == 200
    mock_use_case.execute.assert_called_once()


def test_ingest_youtube_skipped(mock_use_case):
    mock_result = MagicMock()
    mock_result.skipped = True
    mock_result.reason = "This content has already been ingested."
    mock_use_case.execute.return_value = mock_result

    response = client.post(
        "/rest/ingest/youtube", json={"video_url": "https://youtube.com/watch?v=123"}
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "This content has already been ingested."


def test_ingest_youtube_value_error(mock_use_case):
    mock_use_case.execute.side_effect = ValueError("Invalid URL")

    response = client.post("/rest/ingest/youtube", json={"video_url": "invalid"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid URL"


def test_ingest_youtube_exception(mock_use_case):
    mock_use_case.execute.side_effect = Exception("Internal error")

    response = client.post(
        "/rest/ingest/youtube", json={"video_url": "https://youtube.com/watch?v=123"}
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal error"


def test_ingest_youtube_reprocess():
    # Use real dependency override for task_queue if needed,
    # but mock_app_state fixture already sets app.state.task_queue
    from src.presentation.api.dependencies import get_task_queue_service

    mock_queue = MagicMock()
    app.dependency_overrides[get_task_queue_service] = lambda: mock_queue

    try:
        response = client.post(
            "/rest/ingest/youtube",
            json={"video_url": "https://youtube.com/watch?v=123", "reprocess": True},
        )

        assert response.status_code == 200
        assert response.json()["skipped"] is False
        assert response.json()["reason"] == "Ingestion started in background queue."
        assert mock_queue.enqueue.called
    finally:
        app.dependency_overrides.pop(get_task_queue_service, None)
