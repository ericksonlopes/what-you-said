import pytest
from langchain_core.documents import Document
from unittest.mock import MagicMock
from uuid import uuid4
from src.application.use_cases.file_ingestion_use_case import FileIngestionUseCase
from src.application.dtos.commands.ingest_file_command import IngestFileCommand
from src.domain.entities.enums.source_type_enum_entity import SourceType
from src.domain.entities.enums.ingestion_job_status_enum import IngestionJobStatus
from src.domain.entities.enums.content_source_status_enum import ContentSourceStatus


@pytest.mark.FileIngestionUseCase
class TestFileIngestionUseCase:
    @pytest.fixture
    def use_case_deps(self):
        ms = MagicMock()
        ms.model_name = "test-model"
        # Mock model if needed
        ms.model = MagicMock()
        ms.model.tokenizer = MagicMock()
        ms.model.tokenizer.encode.return_value = [1, 2, 3]
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

        # Verify notifications instead of direct service calls
        assert use_case_deps["event_bus"].publish.called

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

        # In the new implementation, _handle_error calls ingestion_service.update_job
        use_case_deps["ingestion_service"].update_job.assert_called_with(
            job_mock.id, IngestionJobStatus.FAILED, error_message="Extraction failed"
        )

    def test_determine_source_type_fallbacks(self, use_case_deps):
        use_case = FileIngestionUseCase(**use_case_deps)

        def check(fname):
            return use_case._determine_source_type_refined(
                IngestFileCommand(file_name=fname)
            )

        assert check("test.docx") == SourceType.DOCX
        assert check("test.doc") == SourceType.DOCX
        assert check("test.pptx") == SourceType.PPTX
        assert check("test.ppt") == SourceType.PPTX
        assert check("test.xlsx") == SourceType.XLSX
        assert check("test.xls") == SourceType.XLSX
        assert check("test.md") == SourceType.MARKDOWN
        assert check("test.markdown") == SourceType.MARKDOWN
        assert check("test.jpg") == SourceType.IMAGE
        assert check("test.png") == SourceType.IMAGE
        assert check("test.txt") == SourceType.TXT
        assert check("test.unknown") == SourceType.OTHER

    def test_execute_rollback_on_failure(self, use_case_deps, mock_extractor):
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
            source_mock.id, ContentSourceStatus.FAILED
        )

    def test_execute_source_type_refinement(
        self, use_case_deps, mock_extractor, monkeypatch
    ):
        use_case = FileIngestionUseCase(**use_case_deps)
        # Force it to be OTHER first so refinement triggers
        monkeypatch.setattr(
            use_case, "_determine_source_type_refined", lambda cmd: SourceType.OTHER
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

        # Mock RecursiveCharacterTextSplitter from its original package
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

    def test_build_chunk_entities_tokenizer_exceptions(self, use_case_deps):
        use_case = FileIngestionUseCase(**use_case_deps)
        tokenizer = use_case_deps["model_loader_service"].model.tokenizer

        # First exception: General failure triggers fallback len//4
        tokenizer.encode.side_effect = Exception("Fatal")
        docs = [MagicMock(page_content="test", metadata={})]
        source = MagicMock(
            id=uuid4(), source_type=SourceType.DOCX, external_source="test.docx"
        )
        subject = MagicMock(id=uuid4())

        chunks = use_case._build_chunk_entities(
            docs,
            source,
            subject,
            IngestFileCommand(file_path="f", file_name="f"),
            uuid4(),
        )
        assert chunks[0].tokens_count == 1  # Fallback: len("test") // 4 = 1
    def test_execute_no_source_path(self, use_case_deps):
        use_case = FileIngestionUseCase(**use_case_deps)
        use_case_deps["ks_service"].get_subject_by_id.return_value = MagicMock(id=uuid4())
        cmd = IngestFileCommand(file_path=None, file_url=None, file_name="f", subject_id=uuid4())
        with pytest.raises(ValueError, match="Neither file_path nor file_url provided"):
            use_case.execute(cmd)

    def test_extract_docs_plain_text_fallback(self, use_case_deps, mock_extractor, monkeypatch):
        use_case = FileIngestionUseCase(**use_case_deps)
        mock_extractor.extract.side_effect = Exception("format not allowed")
        mock_plain = MagicMock()
        mock_plain.extract.return_value = [Document(page_content="plain", metadata={})]
        monkeypatch.setattr(use_case, "plain_text_extractor", mock_plain)
        
        docs = use_case._extract_docs("test.xyz", IngestFileCommand(file_name="test.xyz"))
        assert docs[0].page_content == "plain"

    def test_extract_docs_no_content_error(self, use_case_deps, mock_extractor):
        use_case = FileIngestionUseCase(**use_case_deps)
        mock_extractor.extract.return_value = []
        with pytest.raises(ValueError, match="No content extracted"):
            use_case._extract_docs("f", IngestFileCommand(file_name="f"))

    def test_refine_source_type_branches(self, use_case_deps):
        use_case = FileIngestionUseCase(**use_case_deps)
        
        # Test Case 1: Refined is OTHER (skips)
        docs = [Document(page_content="c", metadata={"docling_source_type": "other"})]
        assert use_case._refine_source_type(docs, SourceType.PDF) == SourceType.PDF
        
        # Test Case 2: Current is YOUTUBE and refined is TXT (skips)
        docs = [Document(page_content="c", metadata={"docling_source_type": "txt"})]
        assert use_case._refine_source_type(docs, SourceType.YOUTUBE) == SourceType.YOUTUBE
        
        # Test Case 3: ValueError in SourceType
        docs = [Document(page_content="c", metadata={"docling_source_type": "invalid_type"})]
        assert use_case._refine_source_type(docs, SourceType.DOCX) == SourceType.DOCX

    def test_get_or_create_job_reuse(self, use_case_deps):
        use_case = FileIngestionUseCase(**use_case_deps)
        job_id = uuid4()
        mock_job = MagicMock(id=job_id)
        use_case_deps["ingestion_service"].get_by_id.return_value = mock_job
        
        cmd = IngestFileCommand(file_path="f", file_name="f", ingestion_job_id=job_id)
        job = use_case._get_or_create_job(cmd, SourceType.PDF, "ext")
        assert job == mock_job

    def test_resolve_subject_missing_id_and_name(self, use_case_deps):
        use_case = FileIngestionUseCase(**use_case_deps)
        cmd = IngestFileCommand(file_path="f", file_name="f", subject_id=None, subject_name=None)
        with pytest.raises(ValueError, match="Subject missing"):
            use_case._resolve_subject(cmd)

    def test_determine_source_type_refined_v_youtube(self, use_case_deps):
        use_case = FileIngestionUseCase(**use_case_deps)
        
        # From cmd.source_type
        cmd = IngestFileCommand(file_name="f", source_type="pdf")
        assert use_case._determine_source_type_refined(cmd) == SourceType.PDF

        # From cmd.source_type (invalid)
        cmd = IngestFileCommand(file_name="test.txt", source_type="garbage")
        assert use_case._determine_source_type_refined(cmd) == SourceType.TXT

        # YouTube from external_source
        cmd = IngestFileCommand(file_name="f", external_source="https://youtube.com/watch?v=123")
        assert use_case._determine_source_type_refined(cmd) == SourceType.YOUTUBE

    def test_cleanup_temp_dir(self, use_case_deps, monkeypatch):
        use_case = FileIngestionUseCase(**use_case_deps)
        mock_rmtree = MagicMock()
        mock_remove = MagicMock()
        monkeypatch.setattr("os.path.exists", lambda x: True)
        monkeypatch.setattr("shutil.rmtree", mock_rmtree)
        monkeypatch.setattr("os.remove", mock_remove)
        
        # Temp dir
        cmd = IngestFileCommand(file_path="/tmp/dir/file.txt", file_name="f", delete_after_ingestion=True)
        use_case._cleanup(cmd)
        mock_rmtree.assert_called_once()
        
        # Single file
        mock_rmtree.reset_mock()
        cmd = IngestFileCommand(file_path="/data/file.txt", file_name="f", delete_after_ingestion=True)
        use_case._cleanup(cmd)
        mock_remove.assert_called_once()
