import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app
from src.presentation.api.dependencies import (
    get_chunk_index_service,
    get_duplicate_repo,
    get_duplicate_service,
)

client = TestClient(app)

@pytest.mark.DuplicateRouter
class TestDuplicateRouter:
    def test_list_duplicates(self):
        mock_repo = MagicMock()
        app.dependency_overrides[get_duplicate_repo] = lambda: mock_repo
        
        mock_repo.list_duplicates.return_value = ([], 0)
        
        response = client.get("/rest/duplicates")
        assert response.status_code == 200
        assert response.json()["total"] == 0
        
        app.dependency_overrides.clear()

    def test_update_duplicate_status(self):
        mock_repo = MagicMock()
        app.dependency_overrides[get_duplicate_repo] = lambda: mock_repo
        
        # Use a service mock instead because the router calls resolved_duplicate on service
        # Wait, the router calls service.resolve_duplicate
        mock_service = MagicMock()
        app.dependency_overrides[get_duplicate_service] = lambda: mock_service
        
        duplicate_id = str(uuid.uuid4())
        mock_service.resolve_duplicate.return_value = True
        
        response = client.patch(f"/rest/duplicates/{duplicate_id}/status", json={"status": "reviewed"})
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        
        app.dependency_overrides.clear()

    def test_deactivate_chunk(self):
        mock_service = MagicMock()
        app.dependency_overrides[get_duplicate_service] = lambda: mock_service
        
        chunk_id = str(uuid.uuid4())
        mock_service.deactivate_chunk.return_value = True
        
        response = client.post(f"/rest/duplicates/chunks/{chunk_id}/deactivate")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        
        app.dependency_overrides.clear()

    def test_trigger_duplicate_analysis(self):
        mock_service = MagicMock()
        app.dependency_overrides[get_duplicate_service] = lambda: mock_service
        mock_chunk_service = MagicMock()
        app.dependency_overrides[get_chunk_index_service] = lambda: mock_chunk_service
        
        mock_chunk_service.list_chunks.return_value = []
        mock_service.find_and_register_duplicates.return_value = 0
        
        response = client.post("/rest/duplicates/analyze-all")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        
        app.dependency_overrides.clear()
