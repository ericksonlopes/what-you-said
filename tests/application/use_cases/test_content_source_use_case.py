import pytest
import uuid
from unittest.mock import MagicMock
from src.application.use_cases.content_source_use_case import ContentSourceUseCase


@pytest.fixture
def mock_services():
    return {
        "cs_service": MagicMock(),
        "chunk_service": MagicMock(),
        "vector_repo": MagicMock(),
    }


@pytest.fixture
def use_case(mock_services):
    return ContentSourceUseCase(**mock_services)


def test_delete_source_success(use_case, mock_services):
    source_id = uuid.uuid4()
    mock_services["cs_service"].get_by_id.return_value = MagicMock(id=source_id)
    mock_services["chunk_service"].delete_by_content_source.return_value = 5
    mock_services["vector_repo"].delete.return_value = 5
    mock_services["cs_service"].delete_source.return_value = True

    success = use_case.delete(source_id)

    assert success is True
    mock_services["cs_service"].get_by_id.assert_called_once_with(source_id)
    mock_services["chunk_service"].delete_by_content_source.assert_called_once_with(
        source_id
    )
    mock_services["vector_repo"].delete.assert_called_once()
    mock_services["cs_service"].delete_source.assert_called_once_with(source_id)


def test_delete_source_not_found(use_case, mock_services):
    source_id = uuid.uuid4()
    mock_services["cs_service"].get_by_id.return_value = None

    success = use_case.delete(source_id)

    assert success is False
    mock_services["cs_service"].get_by_id.assert_called_once_with(source_id)
    mock_services["chunk_service"].delete_by_content_source.assert_not_called()


def test_delete_source_exception(use_case, mock_services):
    source_id = uuid.uuid4()
    mock_services["cs_service"].get_by_id.return_value = MagicMock(id=source_id)
    mock_services["chunk_service"].delete_by_content_source.side_effect = Exception(
        "DB error"
    )

    with pytest.raises(Exception, match="DB error"):
        use_case.delete(source_id)
