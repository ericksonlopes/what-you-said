import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from src.infrastructure.services.ingestion_job_service import IngestionJobService
from src.domain.entities.enums.ingestion_job_status_enum import IngestionJobStatus
from src.infrastructure.repositories.sql.models.ingestion_job import IngestionJobModel


@pytest.mark.IngestionJobService
class TestIngestionJobService:
    @pytest.fixture
    def mock_repo(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_repo):
        return IngestionJobService(repository=mock_repo)

    def create_mock_model(self, **kwargs):
        jid = kwargs.get("id", uuid4())
        model = IngestionJobModel(
            id=jid,
            content_source_id=kwargs.get("content_source_id", uuid4()),
            status=kwargs.get("status", "started"),
            status_message=kwargs.get("status_message", "msg"),
            error_message=kwargs.get("error_message", None),
            current_step=kwargs.get("current_step", 1),
            total_steps=kwargs.get("total_steps", 5),
            ingestion_type=kwargs.get("ingestion_type", "youtube"),
            chunks_count=kwargs.get("chunks_count", 10),
            embedding_model=kwargs.get("embedding_model", "emb"),
            pipeline_version=kwargs.get("pipeline_version", "1.0"),
            started_at=kwargs.get("started_at", datetime.now(timezone.utc)),
            finished_at=kwargs.get("finished_at", None),
        )
        return model

    def test_create_job(self, service, mock_repo):
        jid = uuid4()
        mock_repo.create_job.return_value = jid
        mock_repo.get_by_id.return_value = self.create_mock_model(id=jid)

        result = service.create_job(
            content_source_id=uuid4(),
            status=IngestionJobStatus.STARTED,
            embedding_model="emb",
            pipeline_version="1.0",
            ingestion_type="youtube",
            vector_store_type="weaviate",
        )

        assert result.id == jid
        mock_repo.create_job.assert_called_once_with(
            content_source_id=mock_repo.create_job.call_args.kwargs.get(
                "content_source_id"
            ),
            status="started",
            embedding_model="emb",
            pipeline_version="1.0",
            ingestion_type="youtube",
            vector_store_type="weaviate",
            source_title=None,
            external_source=None,
            subject_id=None,
        )

    def test_update_job(self, service, mock_repo):
        jid = uuid4()

        service.update_job(
            job_id=jid,
            status=IngestionJobStatus.PROCESSING,
            status_message="working",
            current_step=2,
        )
        mock_repo.update_job.assert_called_once_with(
            job_id=jid,
            status="processing",
            error_message=None,
            status_message="working",
            current_step=2,
            total_steps=None,
            chunks_count=None,
            source_title=None,
            content_source_id=None,
            ingestion_type=None,
        )

    def test_link_job_to_source(self, service, mock_repo):
        jid = uuid4()
        sid = uuid4()
        service.link_job_to_source(jid, sid, "pdf")
        mock_repo.link_job_to_source.assert_called_once_with(
            job_id=jid, content_source_id=sid, ingestion_type="pdf"
        )

    def test_get_by_id(self, service, mock_repo):
        jid = uuid4()
        mock_repo.get_by_id.return_value = self.create_mock_model(id=jid)
        result = service.get_by_id(jid)
        assert result.id == jid

        mock_repo.get_by_id.return_value = None
        assert service.get_by_id(uuid4()) is None

    def test_list_by_content_source(self, service, mock_repo):
        sid = uuid4()
        mock_repo.list_by_content_source.return_value = [self.create_mock_model()]
        result = service.list_by_content_source(sid)
        assert len(result) == 1
        mock_repo.list_by_content_source.assert_called_once_with(sid)

    def test_list_recent_jobs(self, service, mock_repo):
        mock_repo.list_recent_jobs.return_value = [self.create_mock_model()]
        result = service.list_recent_jobs(limit=5, offset=0)
        assert len(result) == 1
        mock_repo.list_recent_jobs.assert_called_once_with(limit=5, offset=0)

    def test_list_recent_jobs_by_subject(self, service, mock_repo):
        sid = uuid4()
        mock_repo.list_recent_jobs_by_subject.return_value = [self.create_mock_model()]
        result = service.list_recent_jobs_by_subject(sid, limit=5, offset=0)
        assert len(result) == 1
        mock_repo.list_recent_jobs_by_subject.assert_called_once_with(
            sid, limit=5, offset=0
        )
