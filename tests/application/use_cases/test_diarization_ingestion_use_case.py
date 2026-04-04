import pytest
from langchain_core.documents import Document
from src.domain.entities.enums.source_type_enum_entity import SourceType
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
            id=diarization_id,
            title="T",
            status="completed",
            source_type="youtube",
            segments=[],
        )
        db.add(record)
        db.commit()

        use_case_deps["ks_service"].get_subject_by_id.return_value = None
        cmd = IngestDiarizationCommand(
            diarization_id=diarization_id, subject_id=uuid4()
        )

        with pytest.raises(ValueError, match="Subject not found"):
            use_case.execute(cmd)

    def test_execute_reprocess(self, use_case_deps, sqlite_memory):
        use_case = DiarizationIngestionUseCase(**use_case_deps)
        db = sqlite_memory

        diarization_id = str(uuid4())
        record = DiarizationRecord(
            id=diarization_id,
            title="Test",
            status="completed",
            source_type="youtube",
            external_source="https://youtube.com/watch?v=123",
            segments=[{"start": 0, "end": 1, "text": "H", "speaker": "S1"}],
        )
        db.add(record)
        db.commit()

        subject_id = uuid4()
        use_case_deps["ks_service"].get_subject_by_id.return_value = MagicMock(
            id=subject_id
        )
        use_case_deps["cs_service"].get_by_source_info.return_value = MagicMock(
            id=uuid4()
        )

        cmd = IngestDiarizationCommand(
            diarization_id=diarization_id, subject_id=subject_id, reprocess=True
        )

        use_case.execute(cmd)
        assert use_case_deps["chunk_service"].delete_by_content_source.called
        assert use_case_deps["vector_service"].delete.called

    def test_execute_error_handling(self, use_case_deps, sqlite_memory):
        use_case = DiarizationIngestionUseCase(**use_case_deps)
        db = sqlite_memory

        diarization_id = str(uuid4())
        record = DiarizationRecord(
            id=diarization_id,
            title="Test",
            status="completed",
            source_type="youtube",
            external_source="https://youtube.com/watch?v=123",
            segments=[{"start": 0, "end": 1, "text": "H", "speaker": "S1"}],
        )
        db.add(record)
        db.commit()

        use_case_deps["ks_service"].get_subject_by_id.side_effect = Exception(
            "Service error"
        )

        cmd = IngestDiarizationCommand(
            diarization_id=diarization_id, subject_id=uuid4()
        )

        with pytest.raises(Exception, match="Service error"):
            use_case.execute(cmd)

    def test_execute_failure_after_job_creation(self, use_case_deps, sqlite_memory):
        use_case = DiarizationIngestionUseCase(**use_case_deps)
        db = sqlite_memory

        diarization_id = str(uuid4())
        record = DiarizationRecord(
            id=diarization_id,
            title="Test",
            status="completed",
            source_type="youtube",
            external_source="https://youtube.com/watch?v=123",
            segments=[{"start": 0, "end": 1, "text": "H", "speaker": "S1"}],
        )
        db.add(record)
        db.commit()

        use_case_deps["ks_service"].get_subject_by_id.return_value = MagicMock(
            id=uuid4()
        )
        job_mock = MagicMock(id=uuid4())
        use_case_deps["ingestion_service"].create_job.return_value = job_mock
        # Fail at _get_or_create_source
        use_case_deps["cs_service"].get_by_source_info.side_effect = Exception(
            "Late error"
        )

        cmd = IngestDiarizationCommand(
            diarization_id=diarization_id, subject_id=uuid4()
        )

        with pytest.raises(Exception, match="Late error"):
            use_case.execute(cmd)

        use_case_deps["ingestion_service"].update_job.assert_any_call(
            job_id=job_mock.id,
            status=pytest.importorskip(
                "src.domain.entities.enums.ingestion_job_status_enum"
            ).IngestionJobStatus.FAILED,
            error_message="Late error",
        )

    def test_resolve_source_info_upload(self, use_case_deps):
        use_case = DiarizationIngestionUseCase(**use_case_deps)
        record = MagicMock()
        record.source_type = "upload"
        record.external_source = "s3://path"
        record.source_metadata = None

        st, es = use_case._resolve_source_info(record)
        assert (
            st
            == pytest.importorskip(
                "src.domain.entities.enums.source_type_enum_entity"
            ).SourceType.AUDIO
        )
        assert es == "s3://path"

    def test_format_transcript_long_audio(self, use_case_deps):
        use_case = DiarizationIngestionUseCase(**use_case_deps)
        segments = [{"start": 3661, "end": 3665, "text": "Long time", "speaker": "S1"}]
        formatted = use_case._format_transcript(segments, {"mapping": {}})
        assert "[01:01:01 - 01:01:05]" in formatted

    def test_execute_empty_transcript_error(self, use_case_deps, sqlite_memory):
        use_case = DiarizationIngestionUseCase(**use_case_deps)
        db = sqlite_memory
        diarization_id = str(uuid4())
        record = DiarizationRecord(
            id=diarization_id,
            title="T",
            segments=[],
            source_type="youtube",
            status="completed",
        )
        db.add(record)
        db.commit()
        use_case_deps["ks_service"].get_subject_by_id.return_value = MagicMock(
            id=uuid4()
        )

        cmd = IngestDiarizationCommand(
            diarization_id=diarization_id, subject_id=uuid4()
        )
        with pytest.raises(ValueError, match="No segments found"):
            use_case.execute(cmd)

    def test_resolve_source_info_branches(self, use_case_deps):
        use_case = DiarizationIngestionUseCase(**use_case_deps)

        # Test 1: Invalid source_type -> OTHER
        record = MagicMock(
            source_type="garbage", external_source="url", source_metadata=None
        )
        st, es = use_case._resolve_source_info(record)
        assert st == SourceType.OTHER

        # Test 2: Source metadata with original_url
        record = MagicMock(
            source_type="youtube",
            external_source="yt-url",
            source_metadata={"original_url": "orig-url"},
        )
        st, es = use_case._resolve_source_info(record)
        assert es == "orig-url"

    def test_generate_split_docs_no_tokenizer(self, use_case_deps, monkeypatch):
        use_case = DiarizationIngestionUseCase(**use_case_deps)
        use_case.model_loader_service.model = None  # No model/tokenizer

        record = MagicMock(source_metadata={"meta": "data"})
        mock_splitter = MagicMock()
        mock_splitter.split_documents.return_value = [
            Document(page_content="c", metadata={})
        ]
        monkeypatch.setattr(
            "langchain_text_splitters.RecursiveCharacterTextSplitter",
            lambda **kwargs: mock_splitter,
        )

        docs = use_case._generate_split_docs(
            "text",
            "title",
            "source",
            SourceType.PDF,
            IngestDiarizationCommand(diarization_id=uuid4(), subject_id=uuid4()),
            record,
        )
        assert len(docs) == 1
        mock_splitter.split_documents.assert_called_once()

    def test_execute_with_existing_job_id(self, use_case_deps, sqlite_memory):
        use_case = DiarizationIngestionUseCase(**use_case_deps)
        db = sqlite_memory
        diarization_id = str(uuid4())
        record = DiarizationRecord(
            id=diarization_id,
            title="T",
            source_type="youtube",
            segments=[{"text": "h", "start": 0, "end": 1}],
            status="completed",
        )
        db.add(record)
        db.commit()

        job_id = uuid4()
        mock_job = MagicMock(id=job_id)
        use_case_deps["ingestion_service"].get_by_id.return_value = mock_job
        use_case_deps["ks_service"].get_subject_by_id.return_value = MagicMock(
            id=uuid4()
        )
        use_case_deps["cs_service"].create_source.return_value = MagicMock(id=uuid4())

        cmd = IngestDiarizationCommand(
            diarization_id=diarization_id, subject_id=uuid4(), ingestion_job_id=job_id
        )
        result = use_case.execute(cmd)
        assert result["job_id"] == job_id
        use_case_deps["ingestion_service"].get_by_id.assert_called_with(job_id)
