import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from main import app
from src.presentation.api.dependencies import get_ks_service

client = TestClient(app)

@pytest.fixture
def mock_ks_service():
    mock = MagicMock()
    app.dependency_overrides[get_ks_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_ks_service, None)

def test_create_subject_success(mock_ks_service):
    mock_ks_service.create_subject.return_value = {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "name": "test",
        "description": "desc",
        "icon": "icon"
    }
    
    response = client.post("/rest/subjects", json={"name": "test", "description": "desc"})
    
    assert response.status_code == 201
    mock_ks_service.create_subject.assert_called_once()

def test_create_subject_error(mock_ks_service):
    mock_ks_service.create_subject.side_effect = Exception("Error")
    
    response = client.post("/rest/subjects", json={"name": "test"})
    
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"

def test_get_subjects_success(mock_ks_service):
    mock_ks_service.list_subjects.return_value = []
    
    response = client.get("/rest/subjects")
    
    assert response.status_code == 200
    assert response.json() == []
    mock_ks_service.list_subjects.assert_called_once()

def test_get_subjects_error(mock_ks_service):
    mock_ks_service.list_subjects.side_effect = Exception("Error")
    
    response = client.get("/rest/subjects")
    
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
