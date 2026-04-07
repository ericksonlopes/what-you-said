from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from main import app
from src.presentation.api.dependencies import (
    get_chunk_index_service,
    get_chunk_vector_service,
)

client = TestClient(app)


@pytest.fixture
def mock_chunk_index_service():
    mock = MagicMock()
    app.dependency_overrides[get_chunk_index_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_chunk_index_service, None)


@pytest.fixture
def mock_chunk_vector_service():
    mock = MagicMock()
    app.dependency_overrides[get_chunk_vector_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_chunk_vector_service, None)


def test_get_chunks_success(mock_chunk_index_service):
    mock_chunk_index_service.list_chunks.return_value = []
    response = client.get("/rest/chunks")
    assert response.status_code == 200
    assert response.json() == []
    mock_chunk_index_service.list_chunks.assert_called_once()


def test_get_chunks_error(mock_chunk_index_service):
    mock_chunk_index_service.list_chunks.side_effect = Exception("Database error")
    response = client.get("/rest/chunks")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}


def test_update_chunk_success(mock_chunk_index_service, mock_chunk_vector_service):
    chunk_id = uuid4()
    mock_entity = MagicMock()
    mock_chunk_index_service.get_by_id.return_value = mock_entity
    mock_chunk_index_service.update_chunk.return_value = True

    response = client.patch(f"/rest/chunks/{chunk_id}", json={"content": "new content"})

    assert response.status_code == 200
    assert response.json() is True
    mock_chunk_index_service.get_by_id.assert_called_once()
    mock_chunk_index_service.update_chunk.assert_called_once_with(chunk_id, "new content")
    mock_chunk_vector_service.delete_by_id.assert_called_once_with(chunk_id)
    mock_chunk_vector_service.index_documents.assert_called_once()


def test_update_chunk_not_found(mock_chunk_index_service):
    chunk_id = uuid4()
    mock_chunk_index_service.get_by_id.return_value = None

    response = client.patch(f"/rest/chunks/{chunk_id}", json={"content": "new content"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Chunk not found"}


def test_update_chunk_failed_sql(mock_chunk_index_service):
    chunk_id = uuid4()
    mock_chunk_index_service.get_by_id.return_value = MagicMock()
    mock_chunk_index_service.update_chunk.return_value = False

    response = client.patch(f"/rest/chunks/{chunk_id}", json={"content": "new content"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Failed to update chunk in SQL"}


def test_update_chunk_error(mock_chunk_index_service):
    chunk_id = uuid4()
    mock_chunk_index_service.get_by_id.side_effect = Exception("Unexpected error")

    response = client.patch(f"/rest/chunks/{chunk_id}", json={"content": "new content"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Unexpected error"}


def test_delete_chunk_success(mock_chunk_index_service, mock_chunk_vector_service):
    chunk_id = uuid4()
    mock_chunk_index_service.delete_chunk.return_value = True

    response = client.delete(f"/rest/chunks/{chunk_id}")

    assert response.status_code == 200
    assert response.json() is None
    mock_chunk_index_service.delete_chunk.assert_called_once_with(chunk_id)
    mock_chunk_vector_service.delete_by_id.assert_called_once_with(chunk_id)


def test_delete_chunk_not_found(mock_chunk_index_service):
    chunk_id = uuid4()
    mock_chunk_index_service.delete_chunk.return_value = False

    response = client.delete(f"/rest/chunks/{chunk_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Chunk not found in SQL"}


def test_delete_chunk_error(mock_chunk_index_service):
    chunk_id = uuid4()
    mock_chunk_index_service.delete_chunk.side_effect = Exception("Unexpected error")

    response = client.delete(f"/rest/chunks/{chunk_id}")

    assert response.status_code == 500
    assert response.json() == {"detail": "Unexpected error"}
