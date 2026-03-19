import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from main import app
from src.presentation.api.dependencies import get_cs_service, get_model_loader

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


def test_get_source_types():
    response = client.get("/rest/sources/types")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert "youtube" in data
    assert "pdf" in data


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
    # ModelLoaderService is usually a mock here, but if we want to trigger the except block:
    # We can use a property mock or just side_effect if it were a method
    # Since it's accessing attributes, we might need to mock the whole service to fail on access
    # but the router code accesses attributes.

    # Let's mock it to raise exception on access if possible, or just mock the dependency to raise.
    app.dependency_overrides[get_model_loader] = MagicMock(
        side_effect=Exception("Error")
    )

    try:
        client.get("/rest/sources/model")
        # FastAPI handles dependency exception usually before the router try-except if it's in Depends
        # but the router has its own try-except.
        # If the dependency itself raises, it's a 500 from FastAPI.
        # If the router code raises while using the service, it's our 500.
    finally:
        app.dependency_overrides.pop(get_model_loader, None)
