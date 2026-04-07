from src.infrastructure.repositories.sql.diarization_repository import (
    DiarizationRepository,
)
from src.domain.entities.diarization import DiarizationResult, Segment
from src.domain.entities.enums.diarization_status_enum import DiarizationStatus


class TestDiarizationRepository:
    def test_create_pending(self, sqlite_memory):
        repo = DiarizationRepository(sqlite_memory)
        record = repo.create_pending("Title", "youtube", "http", "pt", "base")

        assert record.id is not None
        assert record.status == DiarizationStatus.PENDING.value
        assert record.name == "Title"

    def test_save_new_and_update(self, sqlite_memory):
        repo = DiarizationRepository(sqlite_memory)
        result = DiarizationResult(
            segments=[Segment(start=0, end=1, text="t", speaker="S1")], language="en"
        )

        # Save new
        record = repo.save(result, "T1", "upload", "f1", "/folder")
        assert record.status == DiarizationStatus.PROCESSING.value
        assert len(record.segments) == 1

        # Update existing
        result2 = DiarizationResult(segments=[], language="fr")
        updated = repo.save(
            result2, "T2", "upload", "f1", "/folder2", diarization_id=record.id
        )
        assert updated.id == record.id
        assert updated.name == "T2"
        assert updated.language == "fr"

    def test_update_status_and_recognition(self, sqlite_memory):
        repo = DiarizationRepository(sqlite_memory)
        record = repo.create_pending("T", "y", "h", "pt")

        repo.update_status(
            record.id,
            DiarizationStatus.FAILED.value,
            error_message="Error X",
            status_message="Msg Y",
        )
        assert record.status == DiarizationStatus.FAILED.value
        assert record.error_message == "Error X"
        assert record.status_message == "Msg Y"

        repo.update_recognition_results(record.id, {"mapping": {"A": "B"}})
        assert record.recognition_results["mapping"]["A"] == "B"

    def test_get_all_and_delete(self, sqlite_memory):
        repo = DiarizationRepository(sqlite_memory)
        r1 = repo.create_pending("T1", "y", "h", "pt")
        repo.create_pending("T2", "y", "h", "pt")

        all_recs = repo.get_all(limit=10)

        assert len(all_recs) == 2

        repo.delete(r1.id)
        assert len(repo.get_all()) == 1
        assert repo.get_by_id(r1.id) is None
