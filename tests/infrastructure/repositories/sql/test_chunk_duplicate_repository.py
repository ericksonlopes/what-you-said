import uuid

import pytest

from src.infrastructure.repositories.sql.chunk_duplicate_repository import ChunkDuplicateSQLRepository
from src.infrastructure.repositories.sql.models.content_source import ContentSourceModel
from src.infrastructure.repositories.sql.models.knowledge_subject import KnowledgeSubjectModel


@pytest.mark.ChunkDuplicateSQLRepository
def test_create_duplicate_record(sqlite_memory):
    """Test creating a duplicate record in the repository."""
    repo = ChunkDuplicateSQLRepository()
    chunk_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    similarity = 0.95
    status = "pending"
    
    record = repo.create_duplicate_record(chunk_ids, similarity, status)
    
    assert record.id is not None
    assert record.chunk_ids == chunk_ids
    assert record.similarity == pytest.approx(similarity)
    assert record.status == status

@pytest.mark.ChunkDuplicateSQLRepository
def test_list_duplicates_filtering(sqlite_memory):
    """Test listing duplicates with status and subject filtering."""
    db = sqlite_memory
    repo = ChunkDuplicateSQLRepository()
    
    # Create a subject and content source
    subject = KnowledgeSubjectModel(name="Test Subject")
    db.add(subject)
    db.commit()
    db.refresh(subject)
    
    source = ContentSourceModel(
        subject_id=subject.id,
        source_type="file",
        external_source="test.txt"
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    
    # Create duplicate records
    repo.create_duplicate_record([str(uuid.uuid4())], 0.9, "pending", content_source_id=source.id)
    repo.create_duplicate_record([str(uuid.uuid4())], 0.8, "reviewed", content_source_id=source.id)
    
    # List all
    _, total = repo.list_duplicates()
    assert total == 2
    
    # Filter by status
    pending_items, total = repo.list_duplicates(status="pending")
    assert total == 1
    assert pending_items[0].status == "pending"
    
    # Filter by subject_id
    _, total = repo.list_duplicates(subject_ids=[str(subject.id)])
    assert total == 2
    
    # Filter with non-existent subject
    _, total = repo.list_duplicates(subject_ids=[str(uuid.uuid4())])
    assert total == 0

@pytest.mark.ChunkDuplicateSQLRepository
def test_update_status(sqlite_memory):
    """Test updating the status of a duplicate record."""
    repo = ChunkDuplicateSQLRepository()
    record = repo.create_duplicate_record([str(uuid.uuid4())], 0.9, "pending")
    
    success = repo.update_status(record.id, "reviewed")
    assert success is True
    
    updated = repo.get_by_id(record.id)
    assert updated is not None
    assert updated.status == "reviewed"

@pytest.mark.ChunkDuplicateSQLRepository
def test_delete_record(sqlite_memory):
    """Test deleting a duplicate record."""
    repo = ChunkDuplicateSQLRepository()
    record = repo.create_duplicate_record([str(uuid.uuid4())], 0.9, "pending")
    
    success = repo.delete_record(record.id)
    assert success is True
    
    deleted = repo.get_by_id(record.id)
    assert deleted is None
