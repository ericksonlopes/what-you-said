import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from main import app
from src.presentation.api.dependencies import (
    get_cs_service,
    get_model_loader,
    get_content_source_use_case,
)

client = TestClient(app)


@pytest.fixture
def mock_cs_service():
    mock = MagicMock()
    app.dependency_overrides[get_cs_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_cs_service, None)


@pytest.fixture
def mock_model_loader():
    mock = MagicMock()
    mock.model_name = "test-model"
    mock.dimensions = 384
    mock.max_seq_length = 512
    app.dependency_overrides[get_model_loader] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_model_loader, None)


@pytest.fixture
def mock_delete_use_case():
    mock = MagicMock()
    app.dependency_overrides[get_content_source_use_case] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_content_source_use_case, None)


def test_get_source_types():
    response = client.get("/rest/sources/types")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert "youtube" in data


def test_get_sources_success(mock_cs_service):
    mock_cs_service.list_all.return_value = []

    response = client.get("/rest/sources")

    assert response.status_code == 200
    assert response.json() == []
    mock_cs_service.list_all.assert_called_once()


def test_get_sources_error(mock_cs_service):
    mock_cs_service.list_all.side_effect = Exception("Error")

    response = client.get("/rest/sources")

    assert response.status_code == 500
    assert response.json()["detail"] == "Error"


def test_get_model_info_success(mock_model_loader):
    response = client.get("/rest/sources/model")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-model"
    assert data["dimensions"] == 384
    assert data["max_seq_length"] == 512


def test_get_model_info_error(mock_model_loader):
    # To trigger the router's internal try-except block, we mock an attribute access error.
    type(mock_model_loader).model_name = property(
        lambda x: exec('raise(Exception("attr fail"))')
    )

    response = client.get("/rest/sources/model")
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"


def test_delete_source_success(mock_delete_use_case):
    from uuid import uuid4

    source_id = uuid4()
    mock_delete_use_case.delete.return_value = True

    response = client.delete(f"/rest/sources/{source_id}")

    assert response.status_code == 200
    assert response.json()["success"] is True
    mock_delete_use_case.delete.assert_called_once()


def test_delete_source_not_found(mock_delete_use_case):
    from uuid import uuid4

    source_id = uuid4()
    mock_delete_use_case.delete.return_value = False

    response = client.delete(f"/rest/sources/{source_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Content source not found"


def test_delete_source_invalid_uuid():
    response = client.delete("/rest/sources/not-a-uuid")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid UUID format"


def test_delete_source_internal_error(mock_delete_use_case):
    from uuid import uuid4

    source_id = uuid4()
    mock_delete_use_case.delete.side_effect = Exception("Fatal error")

    response = client.delete(f"/rest/sources/{source_id}")

    assert response.status_code == 500
    assert response.json()["detail"] == "Fatal error"
