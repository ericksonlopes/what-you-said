import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from src.application.use_cases.file_ingestion_use_case import FileIngestionUseCase
from src.application.dtos.commands.ingest_file_command import IngestFileCommand
from src.domain.entities.enums.source_type_enum_entity import SourceType
from src.domain.entities.enums.ingestion_job_status_enum import IngestionJobStatus


@pytest.mark.FileIngestionUseCase
class TestFileIngestionUseCase:
    @pytest.fixture
    def use_case_deps(self):
        ms = MagicMock()
        ms.model_name = "test-model"
        ms.model.tokenizer = MagicMock()
        ms.model.tokenizer.encode.return_value = [1, 2, 3]
        ms.model.tokenizer.decode.return_value = "content"
        return {
            "ks_service": MagicMock(),
            "cs_service": MagicMock(),
            "ingestion_service": MagicMock(),
            "model_loader_service": ms,
            "embedding_service": MagicMock(),
            "chunk_service": MagicMock(),
            "vector_service": MagicMock(),
            "vector_store_type": "weaviate",
        }

    @pytest.fixture
    def mock_extractor(self, monkeypatch):
        mock = MagicMock()
        monkeypatch.setattr(
            "src.application.use_cases.file_ingestion_use_case.DoclingExtractor",
            lambda: mock,
        )
        return mock

    def test_execute_success(self, use_case_deps, mock_extractor):
        use_case = FileIngestionUseCase(**use_case_deps)

        # Setup mocks
        subject_id = uuid4()
        job_id = uuid4()
        source_id = uuid4()

        use_case_deps["ks_service"].get_subject_by_id.return_value = MagicMock(
            id=subject_id
        )
        use_case_deps["ingestion_service"].create_job.return_value = MagicMock(
            id=job_id
        )
        use_case_deps["cs_service"].create_source.return_value = MagicMock(
            id=source_id, source_type=SourceType.DOCX, external_source="test.docx"
        )

        mock_extractor.extract.return_value = [
            MagicMock(page_content="content", metadata={"source": "test.docx"})
        ]
        use_case_deps["vector_service"].index_documents.return_value = ["vec1"]

        cmd = IngestFileCommand(
            file_path="/tmp/test.docx", file_name="test.docx", subject_id=subject_id
        )

        result = use_case.execute(cmd)

        assert result["file_name"] == "test.docx"
        assert result["source_id"] == source_id
        assert result["job_id"] == job_id

        # Verify steps
        use_case_deps["ingestion_service"].update_job.assert_any_call(
            job_id=job_id,
            status=IngestionJobStatus.FINISHED,
            status_message="Ingestion complete!",
            current_step=4,
            total_steps=4,
            chunks_count=1,
        )

    def test_execute_subject_not_found(self, use_case_deps):
        use_case = FileIngestionUseCase(**use_case_deps)
        use_case_deps["ks_service"].get_subject_by_id.return_value = None

        cmd = IngestFileCommand(
            file_path="/tmp/test.docx", file_name="test.docx", subject_id=uuid4()
        )

        with pytest.raises(ValueError, match="Subject not found"):
            use_case.execute(cmd)

    def test_execute_extraction_failure(self, use_case_deps, mock_extractor):
        use_case = FileIngestionUseCase(**use_case_deps)
        use_case_deps["ks_service"].get_subject_by_id.return_value = MagicMock(
            id=uuid4()
        )
        job_mock = MagicMock(id=uuid4())
        use_case_deps["ingestion_service"].create_job.return_value = job_mock
        use_case_deps["ingestion_service"].get_by_id.return_value = job_mock

        mock_extractor.extract.side_effect = Exception("Extraction failed")

        cmd = IngestFileCommand(
            file_path="/tmp/test.docx", file_name="test.docx", subject_id=uuid4()
        )

        with pytest.raises(Exception, match="Extraction failed"):
            use_case.execute(cmd)

        use_case_deps["ingestion_service"].update_job.assert_any_call(
            job_id=job_mock.id,
            status=IngestionJobStatus.FAILED,
            error_message="Extraction failed",
        )
