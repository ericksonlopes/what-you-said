import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from src.application.use_cases.diarization_ingestion_use_case import (
    DiarizationIngestionUseCase,
)
from src.application.dtos.commands.ingest_diarization_command import (
    IngestDiarizationCommand,
)
from src.infrastructure.repositories.sql.models.diarization_record import (
    DiarizationRecord,
)
from src.infrastructure.repositories.sql.diarization_repository import (
    DiarizationRepository,
)


@pytest.mark.DiarizationIngestion
class TestDiarizationIngestionUseCase:
    @pytest.fixture
    def use_case_deps(self, sqlite_memory):
        ms = MagicMock()
        ms.model_name = "test-model"
        ms.model = MagicMock()
        ms.model.tokenizer = MagicMock()
        return {
            "diarization_repo": DiarizationRepository(sqlite_memory),
            "ks_service": MagicMock(),
            "cs_service": MagicMock(),
            "ingestion_service": MagicMock(),
            "model_loader_service": ms,
            "embedding_service": MagicMock(),
            "chunk_service": MagicMock(),
            "vector_service": MagicMock(),
            "vector_store_type": "weaviate",
            "event_bus": MagicMock(),
        }

    def test_execute_success(self, use_case_deps, sqlite_memory):
        use_case = DiarizationIngestionUseCase(**use_case_deps)
        db = sqlite_memory

        # Setup: Create a diarization record
        diarization_id = str(uuid4())
        record = DiarizationRecord(
            id=diarization_id,
            title="Test Video",
            source_type="youtube",
            external_source="https://youtube.com/watch?v=test",
            status="completed",
            segments=[
                {"start": 0.0, "end": 1.0, "text": "Hello", "speaker": "SPEAKER_00"},
                {"start": 1.0, "end": 2.0, "text": "World", "speaker": "SPEAKER_00"},
            ],
            recognition_results={"mapping": {"SPEAKER_00": "User A"}},
            source_metadata={},
        )
        db.add(record)
        db.commit()

        subject_id = uuid4()
        use_case_deps["ks_service"].get_subject_by_id.return_value = MagicMock(
            id=subject_id
        )

        job_mock = MagicMock(id=uuid4())
        use_case_deps["ingestion_service"].create_job.return_value = job_mock
        use_case_deps["cs_service"].get_by_source_info.return_value = None

        source_id = uuid4()
        use_case_deps["cs_service"].create_source.return_value = MagicMock(id=source_id)
        use_case_deps["vector_service"].index_documents.return_value = ["vec1"]

        cmd = IngestDiarizationCommand(
            diarization_id=diarization_id, subject_id=subject_id
        )

        result = use_case.execute(cmd)

        assert result["source_id"] == source_id
        assert result["job_id"] == job_mock.id
        assert use_case_deps["event_bus"].publish.called

    def test_execute_record_not_found(self, use_case_deps):
        use_case = DiarizationIngestionUseCase(**use_case_deps)
        cmd = IngestDiarizationCommand(diarization_id=str(uuid4()), subject_id=uuid4())

        with pytest.raises(ValueError, match="Diarization record not found"):
            use_case.execute(cmd)

    def test_execute_subject_not_found(self, use_case_deps, sqlite_memory):
        use_case = DiarizationIngestionUseCase(**use_case_deps)
        db = sqlite_memory

        diarization_id = str(uuid4())
        record = DiarizationRecord(
            id=diarization_id, title="T", status="completed", segments=[]
        )
        db.add(record)
        db.commit()

        use_case_deps["ks_service"].get_subject_by_id.return_value = None
        cmd = IngestDiarizationCommand(
            diarization_id=diarization_id, subject_id=uuid4()
        )

        with pytest.raises(ValueError, match="Subject not found"):
            use_case.execute(cmd)

    def test_format_transcript_merging(self, use_case_deps):
        use_case = DiarizationIngestionUseCase(**use_case_deps)
        segments = [
            {"start": 0.0, "end": 1.0, "text": "Hello", "speaker": "SPK1"},
            {"start": 1.1, "end": 2.0, "text": "how are you?", "speaker": "SPK1"},
            {"start": 2.1, "end": 3.0, "text": "I am fine", "speaker": "SPK2"},
        ]
        recognition = {"mapping": {"SPK1": "Alice", "SPK2": "Bob"}}

        # Test private method _format_transcript
        formatted = use_case._format_transcript(segments, recognition)

        assert "Alice: Hello how are you?" in formatted
        assert "Bob: I am fine" in formatted
        assert "[00:00 - 00:02]" in formatted
