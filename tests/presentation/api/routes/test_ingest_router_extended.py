import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from main import app
from src.presentation.api.dependencies import get_task_queue_service
from uuid import uuid4

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_app_state():
    app.state.task_queue = MagicMock()
    app.state.event_bus = MagicMock()
    yield

def test_ingest_file_success():
    mock_queue = MagicMock()
    app.dependency_overrides[get_task_queue_service] = lambda: mock_queue
    
    try:
        # Create a dummy file
        file_content = b"test content"
        files = {"file": ("test.pdf", file_content, "application/pdf")}
        data = {
            "subject_id": str(uuid4()),
            "language": "en"
        }
        
        response = client.post("/rest/ingest/file", files=files, data=data)
        
        assert response.status_code == 200
        assert "File upload successful" in response.json()["message"]
        assert mock_queue.enqueue.called
    finally:
        app.dependency_overrides.pop(get_task_queue_service, None)

def test_ingest_file_url_success():
    mock_queue = MagicMock()
    app.dependency_overrides[get_task_queue_service] = lambda: mock_queue
    
    try:
        payload = {
            "file_url": "https://example.com/test.pdf",
            "language": "pt",
            "subject_id": str(uuid4())
        }
        
        response = client.post("/rest/ingest/file-url", json=payload)
        
        assert response.status_code == 200
        assert "File URL ingestion started" in response.json()["message"]
        assert mock_queue.enqueue.called
    finally:
        app.dependency_overrides.pop(get_task_queue_service, None)

def test_ingest_web_success():
    mock_queue = MagicMock()
    app.dependency_overrides[get_task_queue_service] = lambda: mock_queue
    
    try:
        payload = {
            "url": "https://example.com",
            "language": "pt"
        }
        
        response = client.post("/rest/ingest/web", json=payload)
        
        assert response.status_code == 200
        assert "Web scraping ingestion started" in response.json()["message"]
        assert mock_queue.enqueue.called
    finally:
        app.dependency_overrides.pop(get_task_queue_service, None)

def test_ingest_diarization_success():
    mock_queue = MagicMock()
    app.dependency_overrides[get_task_queue_service] = lambda: mock_queue
    
    try:
        payload = {
            "diarization_id": str(uuid4()),
            "subject_id": str(uuid4()),
            "language": "pt"
        }
        
        response = client.post("/rest/ingest/diarization", json=payload)
        
        assert response.status_code == 200
        assert "Diarization ingestion started" in response.json()["message"]
        assert mock_queue.enqueue.called
    finally:
        app.dependency_overrides.pop(get_task_queue_service, None)

def test_ingest_diarization_invalid_uuid():
    payload = {
        "diarization_id": "not-a-uuid",
        "subject_id": str(uuid4())
    }
    
    response = client.post("/rest/ingest/diarization", json=payload)
    
    assert response.status_code == 400
    assert "Invalid UUID format" in response.json()["detail"]
