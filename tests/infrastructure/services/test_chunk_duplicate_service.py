import uuid
from unittest.mock import MagicMock

import pytest

from src.domain.entities.enums.search_mode_enum import SearchMode
from src.infrastructure.services.chunk_duplicate_service import ChunkDuplicateService


@pytest.fixture
def mock_repos():
    repo = MagicMock()
    chunk_repo = MagicMock()
    vector_svc = MagicMock()
    return repo, chunk_repo, vector_svc

def test_find_and_register_duplicates(mock_repos):
    """Test finding and registering duplicates."""
    repo, chunk_repo, vector_svc = mock_repos
    service = ChunkDuplicateService(repo, chunk_repo, vector_svc)
    
    chunk_id = uuid.uuid4()
    mock_chunk = MagicMock()
    mock_chunk.id = chunk_id
    mock_chunk.content = "Duplicate test content"
    mock_chunk.content_source_id = str(uuid.uuid4())
    chunk_repo.get_by_id.return_value = mock_chunk
    
    # Mock similar chunks found
    sim_chunk = MagicMock()
    sim_chunk.id = uuid.uuid4()
    sim_chunk.score = 0.95
    vector_svc.retrieve.return_value = [sim_chunk]
    
    count = service.find_and_register_duplicates([chunk_id], similarity_threshold=0.90)
    
    assert count == 1
    vector_svc.retrieve.assert_called_once_with(
        query=mock_chunk.content,
        top_k=5,
        search_mode=SearchMode.SEMANTIC,
        re_rank=False
    )
    repo.create_duplicate_record.assert_called_once()
    
    # Check arguments of create_duplicate_record
    _, kwargs = repo.create_duplicate_record.call_args
    assert kwargs['similarity'] == pytest.approx(0.95)
    assert str(chunk_id) in kwargs['chunk_ids']
    assert str(sim_chunk.id) in kwargs['chunk_ids']

def test_find_and_register_no_duplicates(mock_repos):
    """Test when no duplicates are found above threshold."""
    repo, chunk_repo, vector_svc = mock_repos
    service = ChunkDuplicateService(repo, chunk_repo, vector_svc)
    
    chunk_id = uuid.uuid4()
    mock_chunk = MagicMock()
    mock_chunk.id = chunk_id
    mock_chunk.content = "Unique content"
    chunk_repo.get_by_id.return_value = mock_chunk
    
    # Sim chunk with low score
    sim_chunk = MagicMock()
    sim_chunk.id = uuid.uuid4()
    sim_chunk.score = 0.5
    vector_svc.retrieve.return_value = [sim_chunk]
    
    count = service.find_and_register_duplicates([chunk_id], similarity_threshold=0.90)
    
    assert count == 0
    repo.create_duplicate_record.assert_not_called()

def test_deactivate_chunk(mock_repos):
    """Test deactivating a chunk."""
    repo, chunk_repo, vector_svc = mock_repos
    service = ChunkDuplicateService(repo, chunk_repo, vector_svc)
    
    chunk_id = uuid.uuid4()
    chunk_repo.update_is_active.return_value = True
    
    success = service.deactivate_chunk(chunk_id)
    
    assert success is True
    chunk_repo.update_is_active.assert_called_once_with(chunk_id, False)
    vector_svc.delete_by_id.assert_called_once_with(chunk_id)
