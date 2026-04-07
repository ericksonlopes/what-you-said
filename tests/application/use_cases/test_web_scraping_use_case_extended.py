import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.documents import Document

from src.application.dtos.commands.ingest_web_command import IngestWebCommand
from src.application.use_cases.web_scraping_use_case import WebScrapingUseCase
from src.domain.entities.enums.content_source_status_enum import ContentSourceStatus
from src.domain.entities.enums.ingestion_job_status_enum import IngestionJobStatus


@pytest.fixture
def mock_deps():
    return {
        "ks_service": MagicMock(),
        "cs_service": MagicMock(),
        "ingestion_service": MagicMock(),
        "model_loader_service": MagicMock(),
        "embedding_service": MagicMock(),
        "chunk_service": MagicMock(),
        "vector_service": MagicMock(),
        "event_bus": MagicMock(),
        "extractor": AsyncMock(),
    }


@pytest.mark.WebScrapingUseCaseExtended
class TestWebScrapingUseCaseExtended:
    @pytest.mark.asyncio
    async def test_resolve_subject_by_id_success(self, mock_deps):
        mock_deps["model_loader_service"].model_name = "test-model"
        use_case = WebScrapingUseCase(**mock_deps, vector_store_type="qdrant")
        subject_id = uuid.uuid4()
        cmd = IngestWebCommand(url="http://test.com", subject_id=str(subject_id))

        mock_subject = MagicMock(id=subject_id)
        mock_deps["ks_service"].get_subject_by_id.return_value = mock_subject
        mock_deps["extractor"].extract.return_value = [
            Document(page_content="content", metadata={"title": "T"})
        ]
        mock_deps["ingestion_service"].create_job.return_value = MagicMock(
            id=uuid.uuid4()
        )
        mock_deps["cs_service"].get_by_source_info.return_value = None
        mock_deps["cs_service"].create_source.return_value = MagicMock(
            id=uuid.uuid4(), external_source="http://test.com"
        )

        await use_case.execute(cmd)

        mock_deps["ks_service"].get_subject_by_id.assert_called_once_with(subject_id)

    @pytest.mark.asyncio
    async def test_execute_extractor_exception_logged_and_raised(self, mock_deps):
        use_case = WebScrapingUseCase(**mock_deps, vector_store_type="qdrant")
        cmd = IngestWebCommand(url="http://test.com", subject_name="S")

        mock_deps["ks_service"].get_by_name.return_value = MagicMock(id=uuid.uuid4())
        mock_deps["extractor"].extract.side_effect = Exception("Scraping error")
        mock_deps["ingestion_service"].create_job.return_value = MagicMock(
            id=uuid.uuid4()
        )

        with pytest.raises(Exception, match="Scraping error"):
            await use_case.execute(cmd)

    @pytest.mark.asyncio
    async def test_resolve_subject_by_name_success(self, mock_deps):
        mock_deps["model_loader_service"].model_name = "test-model"
        use_case = WebScrapingUseCase(**mock_deps, vector_store_type="qdrant")
        cmd = IngestWebCommand(url="http://test.com", subject_name="Test Subject")

        mock_subject = MagicMock(id=uuid.uuid4())
        mock_deps["ks_service"].get_by_name.return_value = mock_subject
        mock_deps["extractor"].extract.return_value = [
            Document(page_content="content", metadata={"title": "T"})
        ]
        mock_deps["ingestion_service"].create_job.return_value = MagicMock(
            id=uuid.uuid4()
        )
        mock_deps["cs_service"].get_by_source_info.return_value = None
        mock_deps["cs_service"].create_source.return_value = MagicMock(
            id=uuid.uuid4(), external_source="http://test.com"
        )

        await use_case.execute(cmd)

        mock_deps["ks_service"].get_by_name.assert_called_once_with("Test Subject")

    @pytest.mark.asyncio
    async def test_resolve_subject_missing_id_raises(self, mock_deps):
        use_case = WebScrapingUseCase(**mock_deps, vector_store_type="qdrant")
        cmd = IngestWebCommand(url="http://test.com", subject_id=str(uuid.uuid4()))
        mock_deps["ks_service"].get_subject_by_id.return_value = None

        with pytest.raises(ValueError, match="Subject not found"):
            await use_case.execute(cmd)

    @pytest.mark.asyncio
    async def test_resolve_subject_missing_name_raises(self, mock_deps):
        use_case = WebScrapingUseCase(**mock_deps, vector_store_type="qdrant")
        cmd = IngestWebCommand(url="http://test.com", subject_name="Nonexistent")
        mock_deps["ks_service"].get_by_name.return_value = None

        with pytest.raises(ValueError, match="Subject not found"):
            await use_case.execute(cmd)

    @pytest.mark.asyncio
    async def test_resolve_subject_none_provided_raises(self, mock_deps):
        use_case = WebScrapingUseCase(**mock_deps, vector_store_type="qdrant")
        cmd = IngestWebCommand(url="http://test.com")

        with pytest.raises(
            ValueError, match="Either subject_id or subject_name must be provided"
        ):
            await use_case.execute(cmd)

    @pytest.mark.asyncio
    async def test_execute_empty_docs_raises(self, mock_deps):
        use_case = WebScrapingUseCase(**mock_deps, vector_store_type="qdrant")
        cmd = IngestWebCommand(url="http://test.com", subject_name="S")
        mock_deps["ks_service"].get_by_name.return_value = MagicMock(id=uuid.uuid4())
        mock_deps["extractor"].extract.return_value = []
        mock_deps["ingestion_service"].create_job.return_value = MagicMock(
            id=uuid.uuid4()
        )

        with pytest.raises(ValueError, match="No content extracted"):
            await use_case.execute(cmd)

    @pytest.mark.asyncio
    async def test_execute_with_existing_job_id(self, mock_deps):
        mock_deps["model_loader_service"].model_name = "test-model"
        job_id = uuid.uuid4()
        use_case = WebScrapingUseCase(**mock_deps, vector_store_type="qdrant")
        cmd = IngestWebCommand(
            url="http://test.com", subject_name="S", ingestion_job_id=str(job_id)
        )

        mock_deps["ks_service"].get_by_name.return_value = MagicMock(id=uuid.uuid4())
        mock_job = MagicMock(id=job_id)
        mock_deps["ingestion_service"].get_by_id.return_value = mock_job
        mock_deps["extractor"].extract.return_value = [
            Document(page_content="content", metadata={"title": "T"})
        ]
        mock_deps["cs_service"].get_by_source_info.return_value = None
        mock_deps["cs_service"].create_source.return_value = MagicMock(
            id=uuid.uuid4(), external_source="http://test.com"
        )

        await use_case.execute(cmd)

        mock_deps["ingestion_service"].get_by_id.assert_called_once_with(job_id)
        mock_deps["ingestion_service"].create_job.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_with_existing_job_id_invalid_uuid_falls_back(
        self, mock_deps
    ):
        mock_deps["model_loader_service"].model_name = "test-model"
        use_case = WebScrapingUseCase(**mock_deps, vector_store_type="qdrant")
        cmd = IngestWebCommand(
            url="http://test.com", subject_name="S", ingestion_job_id="invalid-uuid"
        )

        mock_deps["ks_service"].get_by_name.return_value = MagicMock(id=uuid.uuid4())
        mock_deps["extractor"].extract.return_value = [
            Document(page_content="content", metadata={"title": "T"})
        ]
        mock_deps["cs_service"].get_by_source_info.return_value = None
        mock_deps["cs_service"].create_source.return_value = MagicMock(
            id=uuid.uuid4(), external_source="http://test.com"
        )
        mock_deps["ingestion_service"].create_job.return_value = MagicMock(
            id=uuid.uuid4()
        )

        await use_case.execute(cmd)

        mock_deps["ingestion_service"].create_job.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_reprocess_cleanup(self, mock_deps):
        mock_deps["model_loader_service"].model_name = "test-model"
        use_case = WebScrapingUseCase(**mock_deps, vector_store_type="qdrant")
        cmd = IngestWebCommand(url="http://test.com", subject_name="S", reprocess=True)

        mock_deps["ks_service"].get_by_name.return_value = MagicMock(id=uuid.uuid4())
        mock_deps["extractor"].extract.return_value = [
            Document(page_content="content", metadata={"title": "T"})
        ]
        mock_deps["ingestion_service"].create_job.return_value = MagicMock(
            id=uuid.uuid4()
        )

        source_id = uuid.uuid4()
        mock_source = MagicMock(id=source_id, external_source="http://test.com")
        mock_deps["cs_service"].get_by_source_info.return_value = mock_source

        await use_case.execute(cmd)

        mock_deps["chunk_service"].delete_by_content_source.assert_called_once_with(
            source_id
        )
        mock_deps["vector_service"].delete.assert_called_once_with(
            filters={"content_source_id": str(source_id)}
        )

    @pytest.mark.asyncio
    async def test_execute_reprocess_cleanup_error_ignored(self, mock_deps):
        mock_deps["model_loader_service"].model_name = "test-model"
        use_case = WebScrapingUseCase(**mock_deps, vector_store_type="qdrant")
        cmd = IngestWebCommand(url="http://test.com", subject_name="S", reprocess=True)

        mock_deps["ks_service"].get_by_name.return_value = MagicMock(id=uuid.uuid4())
        mock_deps["extractor"].extract.return_value = [
            Document(page_content="content", metadata={"title": "T"})
        ]
        mock_deps["ingestion_service"].create_job.return_value = MagicMock(
            id=uuid.uuid4()
        )

        source_id = uuid.uuid4()
        mock_source = MagicMock(id=source_id, external_source="http://test.com")
        mock_deps["cs_service"].get_by_source_info.return_value = mock_source
        mock_deps["chunk_service"].delete_by_content_source.side_effect = Exception(
            "Cleanup error"
        )

        # Should not raise exception
        await use_case.execute(cmd)

        mock_deps["chunk_service"].delete_by_content_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_build_chunk_entities_with_tokenizer_success(self, mock_deps):
        mock_model = MagicMock()
        mock_model.tokenizer.encode.return_value = [1, 2, 3]
        mock_deps["model_loader_service"].model = mock_model
        mock_deps["model_loader_service"].model_name = "test-model"

        use_case = WebScrapingUseCase(**mock_deps, vector_store_type="qdrant")

        docs = [Document(page_content="Hello world", metadata={})]
        source = MagicMock(id=uuid.uuid4(), external_source="url")
        subject = MagicMock(id=uuid.uuid4())
        job_id = uuid.uuid4()

        chunks = use_case._build_chunk_entities(
            docs, source, subject, IngestWebCommand(url="url"), job_id
        )

        assert len(chunks) == 1
        assert chunks[0].tokens_count == 3
        mock_model.tokenizer.encode.assert_called_once_with(
            "Hello world", add_special_tokens=False
        )

    @pytest.mark.asyncio
    async def test_build_chunk_entities_with_tokenizer_exception_fallback(
        self, mock_deps
    ):
        mock_model = MagicMock()
        mock_model.tokenizer.encode.side_effect = Exception("Tokenizer error")
        mock_deps["model_loader_service"].model = mock_model
        mock_deps["model_loader_service"].model_name = "test-model"

        use_case = WebScrapingUseCase(**mock_deps, vector_store_type="qdrant")

        docs = [Document(page_content="Hello world", metadata={})]
        source = MagicMock(id=uuid.uuid4(), external_source="url")
        subject = MagicMock(id=uuid.uuid4())
        job_id = uuid.uuid4()

        chunks = use_case._build_chunk_entities(
            docs, source, subject, IngestWebCommand(url="url"), job_id
        )

        assert len(chunks) == 1
        # Fallback is len(page_content) // 4
        assert chunks[0].tokens_count == len("Hello world") // 4

    @pytest.mark.asyncio
    async def test_execute_langchain_splitter_fallback(self, mock_deps):
        # No model/tokenizer on model_loader_service
        mock_deps["model_loader_service"].model = None
        mock_deps["model_loader_service"].model_name = "test-model"

        use_case = WebScrapingUseCase(**mock_deps, vector_store_type="qdrant")
        cmd = IngestWebCommand(url="http://test.com", subject_name="S")

        mock_deps["ks_service"].get_by_name.return_value = MagicMock(id=uuid.uuid4())
        mock_deps["extractor"].extract.return_value = [
            Document(page_content="Very long content " * 100, metadata={"title": "T"})
        ]
        mock_deps["ingestion_service"].create_job.return_value = MagicMock(
            id=uuid.uuid4()
        )
        mock_deps["cs_service"].get_by_source_info.return_value = None
        mock_deps["cs_service"].create_source.return_value = MagicMock(
            id=uuid.uuid4(), external_source="http://test.com"
        )

        await use_case.execute(cmd)

        # Verify it called create_chunks (meaning split worked)
        mock_deps["chunk_service"].create_chunks.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_failure_marks_source_failed(self, mock_deps):
        mock_deps["model_loader_service"].model_name = "test-model"
        use_case = WebScrapingUseCase(**mock_deps, vector_store_type="qdrant")
        cmd = IngestWebCommand(url="http://test.com", subject_name="S")

        mock_deps["ks_service"].get_by_name.return_value = MagicMock(id=uuid.uuid4())
        mock_deps["extractor"].extract.return_value = [
            Document(page_content="content", metadata={"title": "T"})
        ]

        job_id = uuid.uuid4()
        mock_deps["ingestion_service"].create_job.return_value = MagicMock(id=job_id)

        source_id = uuid.uuid4()
        mock_source = MagicMock(id=source_id, external_source="http://test.com")
        mock_deps["cs_service"].get_by_source_info.return_value = mock_source

        # Fail during chunk creation
        mock_deps["chunk_service"].create_chunks.side_effect = Exception(
            "Execute error"
        )

        with pytest.raises(Exception, match="Execute error"):
            await use_case.execute(cmd)

        mock_deps["cs_service"].update_processing_status.assert_called_with(
            content_source_id=source_id,
            status=ContentSourceStatus.FAILED,
            error_message="Execute error",
        )
        mock_deps["ingestion_service"].update_job.assert_called_with(
            job_id=job_id,
            status=IngestionJobStatus.FAILED,
            error_message="Execute error",
        )
