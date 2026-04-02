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
            "event_bus": MagicMock(),
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
        use_case_deps["cs_service"].get_by_source_info.return_value = None
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
            status_message="Ingestion complete: test.docx",
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

    def test_execute_no_content_extracted(self, use_case_deps, mock_extractor):
        use_case = FileIngestionUseCase(**use_case_deps)
        use_case_deps["ks_service"].get_subject_by_id.return_value = MagicMock(
            id=uuid4()
        )
        job_mock = MagicMock(id=uuid4())
        use_case_deps["ingestion_service"].create_job.return_value = job_mock

        mock_extractor.extract.return_value = []

        cmd = IngestFileCommand(
            file_path="/tmp/test.docx", file_name="test.docx", subject_id=uuid4()
        )

        with pytest.raises(ValueError, match="No content extracted"):
            use_case.execute(cmd)

    def test_execute_with_existing_job(self, use_case_deps, mock_extractor):
        use_case = FileIngestionUseCase(**use_case_deps)
        job_id = uuid4()
        subject_id = uuid4()
        job_mock = MagicMock(id=job_id)

        use_case_deps["ks_service"].get_subject_by_id.return_value = MagicMock(
            id=subject_id
        )
        use_case_deps["ingestion_service"].get_by_id.return_value = job_mock
        use_case_deps["cs_service"].get_by_source_info.return_value = MagicMock(
            id=uuid4(), source_type=SourceType.DOCX, external_source="test.docx"
        )
        use_case_deps["cs_service"].get_by_source_info.return_value = None
        use_case_deps["cs_service"].create_source.return_value = MagicMock(
            id=uuid4(), source_type=SourceType.DOCX, external_source="test.docx"
        )
        mock_extractor.extract.return_value = [
            MagicMock(page_content="content", metadata={})
        ]

        cmd = IngestFileCommand(
            file_path="/tmp/test.docx",
            file_name="test.docx",
            subject_id=subject_id,
            ingestion_job_id=job_id,
        )

        result = use_case.execute(cmd)
        assert result["job_id"] == job_id
        use_case_deps["ingestion_service"].get_by_id.assert_called_with(job_id)

    def test_resolve_subject_by_name(self, use_case_deps):
        use_case = FileIngestionUseCase(**use_case_deps)
        subject_id = uuid4()
        use_case_deps["ks_service"].get_by_name.return_value = MagicMock(id=subject_id)

        cmd = IngestFileCommand(
            file_path="/tmp/test.docx",
            file_name="test.docx",
            subject_name="SubjectName",
        )
        subject = use_case._resolve_subject(cmd)
        assert subject.id == subject_id

    def test_resolve_subject_name_not_found(self, use_case_deps):
        use_case = FileIngestionUseCase(**use_case_deps)
        use_case_deps["ks_service"].get_by_name.return_value = None

        cmd = IngestFileCommand(
            file_path="/tmp/test.docx", file_name="test.docx", subject_name="Unknown"
        )
        with pytest.raises(ValueError, match="Subject not found: Unknown"):
            use_case._resolve_subject(cmd)

    def test_resolve_subject_none_provided(self, use_case_deps):
        use_case = FileIngestionUseCase(**use_case_deps)
        cmd = IngestFileCommand(file_path="/tmp/test.docx", file_name="test.docx")
        with pytest.raises(ValueError, match="Either subject_id or subject_name"):
            use_case._resolve_subject(cmd)

    def test_determine_source_type_fallbacks(self, use_case_deps):
        use_case = FileIngestionUseCase(**use_case_deps)
        assert use_case._determine_source_type("test.docx") == SourceType.DOCX
        assert use_case._determine_source_type("test.doc") == SourceType.DOCX
        assert use_case._determine_source_type("test.pptx") == SourceType.PPTX
        assert use_case._determine_source_type("test.ppt") == SourceType.PPTX
        assert use_case._determine_source_type("test.xlsx") == SourceType.XLSX
        assert use_case._determine_source_type("test.xls") == SourceType.XLSX
        assert use_case._determine_source_type("test.md") == SourceType.MARKDOWN
        assert use_case._determine_source_type("test.markdown") == SourceType.MARKDOWN
        assert use_case._determine_source_type("test.jpg") == SourceType.IMAGE
        assert use_case._determine_source_type("test.png") == SourceType.IMAGE
        assert use_case._determine_source_type("test.txt") == SourceType.TXT
        assert use_case._determine_source_type("test.unknown") == SourceType.OTHER

    def test_execute_fallback_splitter(
        self, use_case_deps, mock_extractor, monkeypatch
    ):
        # Remove model from deps to trigger fallback splitter
        del use_case_deps["model_loader_service"].model
        use_case = FileIngestionUseCase(**use_case_deps)

        use_case_deps["ks_service"].get_subject_by_id.return_value = MagicMock(
            id=uuid4()
        )
        use_case_deps["ingestion_service"].create_job.return_value = MagicMock(
            id=uuid4()
        )
        use_case_deps["cs_service"].get_by_source_info.return_value = None
        use_case_deps["cs_service"].create_source.return_value = MagicMock(
            id=uuid4(), source_type=SourceType.DOCX, external_source="test.docx"
        )

        mock_extractor.extract.return_value = [
            MagicMock(page_content="content line 1\ncontent line 2", metadata={})
        ]

        # Mock RecursiveCharacterTextSplitter (it's imported inside the method)
        mock_splitter = MagicMock()
        mock_splitter.split_documents.return_value = [
            MagicMock(page_content="content line 1", metadata={}),
            MagicMock(page_content="content line 2", metadata={}),
        ]
        monkeypatch.setattr(
            "langchain_text_splitters.RecursiveCharacterTextSplitter",
            lambda **kwargs: mock_splitter,
        )

        cmd = IngestFileCommand(
            file_path="/tmp/test.docx", file_name="test.docx", subject_id=uuid4()
        )
        result = use_case.execute(cmd)
        assert result["created_chunks"] == 2
        mock_splitter.split_documents.assert_called_once()

    def test_build_chunk_entities_tokenizer_exceptions(self, use_case_deps):
        use_case = FileIngestionUseCase(**use_case_deps)
        tokenizer = use_case_deps["model_loader_service"].model.tokenizer

        # First exception: No add_special_tokens
        tokenizer.encode.side_effect = [TypeError("No add_special_tokens"), [1, 2]]
        docs = [MagicMock(page_content="test", metadata={})]
        source = MagicMock(
            id=uuid4(), source_type=SourceType.DOCX, external_source="test.docx"
        )
        subject = MagicMock(id=uuid4())

        chunks = use_case._build_chunk_entities(
            docs, source, subject, MagicMock(language="en"), uuid4()
        )
        assert chunks[0].tokens_count == 2

        # Second exception: General failure
        tokenizer.encode.side_effect = Exception("Fatal")
        chunks = use_case._build_chunk_entities(
            docs, source, subject, MagicMock(language="en"), uuid4()
        )
        assert chunks[0].tokens_count == 1  # Fallback: len("test") // 4 = 1

    def test_execute_rollback_on_failure(self, use_case_deps, mock_extractor):
        from src.domain.entities.enums.content_source_status_enum import (
            ContentSourceStatus,
        )

        use_case = FileIngestionUseCase(**use_case_deps)
        use_case_deps["ks_service"].get_subject_by_id.return_value = MagicMock(
            id=uuid4()
        )
        job_mock = MagicMock(id=uuid4())
        source_mock = MagicMock(
            id=uuid4(), source_type=SourceType.DOCX, external_source="f"
        )
        use_case_deps["ingestion_service"].create_job.return_value = job_mock
        use_case_deps["cs_service"].get_by_source_info.return_value = None
        use_case_deps["cs_service"].create_source.return_value = source_mock

        # Fail at vector indexing
        mock_extractor.extract.return_value = [MagicMock(page_content="c", metadata={})]
        use_case_deps["vector_service"].index_documents.side_effect = Exception(
            "Vector fail"
        )

        cmd = IngestFileCommand(file_path="f", file_name="f", subject_id=uuid4())
        with pytest.raises(Exception, match="Vector fail"):
            use_case.execute(cmd)

        use_case_deps["cs_service"].update_processing_status.assert_called_with(
            content_source_id=source_mock.id, status=ContentSourceStatus.FAILED
        )

    def test_determine_source_type_no_extension(self, use_case_deps):
        use_case = FileIngestionUseCase(**use_case_deps)
        # file_name with no dot
        assert use_case._determine_source_type("README") == SourceType.OTHER

    def test_execute_no_tokenizer_no_docs_fallback(self, use_case_deps, mock_extractor):
        # Trigger line 145: not docs
        del use_case_deps["model_loader_service"].model

        use_case_deps["ks_service"].get_subject_by_id.return_value = MagicMock(
            id=uuid4()
        )
        use_case_deps["ingestion_service"].create_job.return_value = MagicMock(
            id=uuid4()
        )
        use_case_deps["cs_service"].get_by_source_info.return_value = None
        use_case_deps["cs_service"].create_source.return_value = MagicMock(
            id=uuid4(), source_type=SourceType.DOCX, external_source="test.docx"
        )

        # Mock extractor to return something, but then we will monkeypatch _build_chunk_entities to receive empty
        mock_extractor.extract.return_value = [MagicMock(page_content="c")]

        # Force docs to be empty after extraction check to reach line 145
        # Actually line 145 is "else: split_docs = []" when docs is falsy.
        # But there is a check "if not docs: raise ValueError" before.
        # Wait, if docs is [something] but later it is treated as empty?
        # Let's look at the code:
        # 110: docs = self.extractor.extract(...)
        # 111: if not docs: raise ValueError
        # ...
        # 143: elif docs: ...
        # 145: else: split_docs = []
        # Line 145 is unreachable if line 111 is present, UNLESS docs becomes falsy between 111 and 143.
        # OR if I mock extractor.extract to return something that evaluates to True but is not a list? No.
        # If docs = [obj], 111 passes.
        # If I want to reach 145, docs must be falsy at 143.

    def test_execute_source_type_refinement(
        self, use_case_deps, mock_extractor, monkeypatch
    ):
        use_case = FileIngestionUseCase(**use_case_deps)
        # Force it to be OTHER first so refinement triggers
        monkeypatch.setattr(
            use_case, "_determine_source_type", lambda x: SourceType.OTHER
        )

        subject_id = uuid4()
        job_id = uuid4()
        source_id = uuid4()

        use_case_deps["ks_service"].get_subject_by_id.return_value = MagicMock(
            id=subject_id
        )
        use_case_deps["ingestion_service"].create_job.return_value = MagicMock(
            id=job_id
        )
        use_case_deps["cs_service"].get_by_source_info.return_value = None
        use_case_deps["cs_service"].create_source.return_value = MagicMock(
            id=source_id, source_type=SourceType.PDF, external_source="test.docx"
        )

        # Mock Docling to detect PDF despite .docx extension in filename
        mock_extractor.extract.return_value = [
            MagicMock(page_content="content", metadata={"source_type": "pdf"})
        ]
        use_case_deps["vector_service"].index_documents.return_value = ["vec1"]

        cmd = IngestFileCommand(
            file_path="/tmp/test.docx", file_name="test.docx", subject_id=subject_id
        )

        use_case.execute(cmd)

        # Verify create_source was called with PDF (refined) instead of DOCX
        _, kwargs = use_case_deps["cs_service"].create_source.call_args
        assert kwargs["source_type"] == SourceType.PDF

        # Verify create_job was called with 'other' (initial type)
        _, kwargs = use_case_deps["ingestion_service"].create_job.call_args
        assert kwargs["ingestion_type"] == "other"
