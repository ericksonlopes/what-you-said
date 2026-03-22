import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from src.application.use_cases.web_scraping_use_case import WebScrapingUseCase
from src.application.dtos.commands.ingest_web_command import IngestWebCommand
from src.domain.entities.enums.ingestion_job_status_enum import IngestionJobStatus
from langchain_core.documents import Document


@pytest.fixture
def mock_dependencies():
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


@pytest.mark.anyio
async def test_web_scraping_use_case_execute_success(mock_dependencies):
    # Setup
    use_case = WebScrapingUseCase(**mock_dependencies, vector_store_type="weaviate")

    cmd = IngestWebCommand(
        url="https://example.com", subject_id=str(uuid.uuid4()), language="en"
    )

    # Mock behavior
    mock_dependencies["ks_service"].get_subject_by_id.return_value = MagicMock(
        id=uuid.uuid4()
    )
    mock_dependencies["extractor"].extract.return_value = [
        Document(page_content="Scraped content", metadata={"title": "Test"})
    ]

    job_mock = MagicMock(id=uuid.uuid4())
    mock_dependencies["ingestion_service"].create_job.return_value = job_mock

    source_mock = MagicMock(id=uuid.uuid4(), external_source=cmd.url)
    mock_dependencies["cs_service"].get_by_source_info.return_value = None
    mock_dependencies["cs_service"].create_source.return_value = source_mock

    mock_dependencies["model_loader_service"].model_name = "test-model"
    mock_dependencies["model_loader_service"].model = None
    mock_dependencies["vector_service"].index_documents.return_value = ["vec-1"]

    # Execute
    result = await use_case.execute(cmd)

    # Assertions
    assert result["url"] == cmd.url
    assert result["created_chunks"] > 0
    assert result["vector_ids"] == ["vec-1"]

    mock_dependencies["extractor"].extract.assert_called_once()
    mock_dependencies["ingestion_service"].create_job.assert_called_once()
    mock_dependencies["cs_service"].create_source.assert_called_once()
    mock_dependencies["vector_service"].index_documents.assert_called_once()


@pytest.mark.anyio
async def test_web_scraping_use_case_extraction_failure(mock_dependencies):
    use_case = WebScrapingUseCase(**mock_dependencies, vector_store_type="weaviate")

    cmd = IngestWebCommand(url="https://fail.com", subject_id=str(uuid.uuid4()))

    mock_dependencies["ks_service"].get_subject_by_id.return_value = MagicMock(
        id=uuid.uuid4()
    )
    mock_dependencies["extractor"].extract.side_effect = Exception("Scraping error")

    job_mock = MagicMock(id=uuid.uuid4())
    mock_dependencies["ingestion_service"].create_job.return_value = job_mock

    with pytest.raises(Exception) as exc:
        await use_case.execute(cmd)

    assert "Scraping error" in str(exc.value)
    mock_dependencies["ingestion_service"].update_job.assert_any_call(
        job_id=job_mock.id,
        status=IngestionJobStatus.FAILED,
        error_message="Scraping error",
    )
