import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app
from src.presentation.api.dependencies import get_settings, get_vector_repository

client = TestClient(app)


@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.app.env = "test"
    settings.app.list_log_levels = ["INFO", "DEBUG"]

    # store_type.value is used in settings_router
    settings.vector.store_type = MagicMock()
    settings.vector.store_type.value = "faiss"

    settings.vector.weaviate_host = "localhost"
    settings.vector.weaviate_port = 8080
    settings.vector.weaviate_grpc_port = 50051
    settings.vector.collection_name_chunks = "Chunks"
    settings.model_embedding.name = "all-MiniLM-L6-v2"
    settings.sql.type = "sqlite"
    settings.sql.database = "test.sqlite"

    settings.redis.host = "localhost"
    settings.redis.port = 6379
    settings.redis.db = 0
    settings.redis.password = None

    app.dependency_overrides[get_settings] = lambda: settings
    yield settings
    app.dependency_overrides.pop(get_settings, None)


@pytest.fixture
def mock_vector_repo():
    mock = MagicMock()
    app.dependency_overrides[get_vector_repository] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_vector_repository, None)


def test_get_current_settings(mock_settings):
    response = client.get("/rest/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["app"]["env"] == "test"
    assert "INFO, DEBUG" in data["app"]["log_levels"]


def test_check_health_api():
    response = client.get("/rest/settings/check/api")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_check_health_sql():
    with patch(
        "src.presentation.api.routes.settings_router.Connector"
    ) as mock_connector:
        mock_session = MagicMock()
        mock_connector.return_value.__enter__.return_value = mock_session

        response = client.get("/rest/settings/check/sql")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_session.execute.assert_called_once()


def test_check_health_vector_ready(mock_vector_repo):
    mock_vector_repo.is_ready.return_value = True
    response = client.get("/rest/settings/check/vector")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_check_health_vector_not_ready(mock_vector_repo):
    mock_vector_repo.is_ready.return_value = False
    response = client.get("/rest/settings/check/vector")
    assert response.status_code == 200
    assert response.json()["status"] == "error"


def test_check_health_model():
    response = client.get("/rest/settings/check/model")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_check_health_unknown():
    response = client.get("/rest/settings/check/unknown")
    assert response.status_code == 200
    assert response.json()["status"] == "error"
    assert "Unknown component" in response.json()["message"]


def test_check_health_exception():
    with patch(
        "src.presentation.api.routes.settings_router.Connector"
    ) as mock_connector:
        mock_connector.side_effect = Exception("Connection failed")
        response = client.get("/rest/settings/check/sql")
        assert response.status_code == 200
        assert response.json()["status"] == "error"
        assert "Connection failed" in response.json()["message"]


def test_check_health_redis(mock_settings, mock_vector_repo):
    with patch("redis.Redis") as mock_redis_class:
        mock_redis = MagicMock()
        mock_redis_class.return_value = mock_redis
        mock_redis.ping.return_value = True

        response = client.get("/rest/settings/check/redis")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_redis.ping.assert_called_once()
