from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app
from src.presentation.api.dependencies import get_search_chunks_use_case

client = TestClient(app)


@pytest.fixture
def mock_use_case():
    mock = MagicMock()
    app.dependency_overrides[get_search_chunks_use_case] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_search_chunks_use_case, None)


def test_search_chunks_success(mock_use_case):
    mock_use_case.execute.return_value = {
        "query": "test query",
        "results": [],
        "total_count": 0,
    }

    response = client.post("/rest/search/", json={"query": "test query", "top_k": 5})

    assert response.status_code == 200
    mock_use_case.execute.assert_called_once()


def test_search_chunks_value_error(mock_use_case):
    mock_use_case.execute.side_effect = ValueError("Invalid query")

    response = client.post("/rest/search/", json={"query": ""})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid query"


def test_search_chunks_exception(mock_use_case):
    mock_use_case.execute.side_effect = Exception("Search failed")

    response = client.post("/rest/search/", json={"query": "test query"})

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
