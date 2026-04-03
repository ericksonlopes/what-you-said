import pytest
from src.infrastructure.repositories.sql.repositories import DiarizationRepository
from src.domain.entities.diarization import DiarizationResult, Segment

@pytest.mark.DiarizationRepository
class TestDiarizationRepository:
    def test_save_and_retrieve(self, sqlite_memory):
        repo = DiarizationRepository(sqlite_memory)
        
        # Prepare mock result
        result = DiarizationResult(
            segments=[Segment(start=0.0, end=1.0, speaker="SPEAKER_00", text="Hello")],
            speakers={"SPEAKER_00"},
            duration=1.0,
            language="en"
        )
        
        record = repo.save(
            result=result,
            title="Test Video",
            source_type="youtube",
            external_source="http://youtube.com/test",
            folder="./data/test",
            storage_path="processed/test"
        )
        
        assert record.id is not None
        assert record.title == "Test Video"
        assert record.segments[0]["text"] == "Hello"
        
        # Test get_by_id
        retrieved = repo.get_by_id(record.id)
        assert retrieved is not None
        assert retrieved.title == "Test Video"
        
        # Test get_all
        all_records = repo.get_all()
        assert len(all_records) == 1

    def test_get_by_id_not_found(self, sqlite_memory):
        repo = DiarizationRepository(sqlite_memory)
        assert repo.get_by_id("non-existent") is None
