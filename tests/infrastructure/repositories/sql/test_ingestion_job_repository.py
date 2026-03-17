from uuid import uuid4, UUID
import pytest
from src.infrastructure.repositories.sql.ingestion_job_repository import IngestionJobSQLRepository
from src.infrastructure.repositories.sql.content_source_repository import ContentSourceSQLRepository
from src.domain.entities.enums.source_type_enum_entity import SourceType

@pytest.mark.IngestionJobRepository
@pytest.mark.usefixtures("sqlite_memory")
class TestIngestionJobSQLRepository:
    def setup_method(self):
        self.repo = IngestionJobSQLRepository()
        self.cs_repo = ContentSourceSQLRepository()

    def _create_source(self, subject_id=None):
        if not subject_id:
            subject_id = uuid4()
        return self.cs_repo.create(
            subject_id=subject_id,
            source_type=SourceType.YOUTUBE.value,
            external_source=f"ext-{uuid4()}",
            title="Test Source",
            language="en"
        )

    def test_create_job_success(self):
        cs_id = self._create_source()
        job_id = self.repo.create_job(content_source_id=cs_id, status="started")
        assert isinstance(job_id, UUID)
        
        job = self.repo.get_by_id(job_id)
        assert job.status == "started"
        assert job.content_source_id == cs_id

    def test_create_job_error(self):
        # Trigger an error by passing invalid content_source_id type if possible, 
        # or just mock the session.
        with pytest.raises(Exception):
            self.repo.create_job(content_source_id="invalid-uuid")

    def test_update_job_success(self):
        job_id = self.repo.create_job(content_source_id=None)
        self.repo.update_job(
            job_id=job_id, 
            status="finished", 
            error_message="no error",
            status_message="done",
            current_step=10,
            total_steps=10,
            chunks_count=5
        )
        
        job = self.repo.get_by_id(job_id)
        assert job.status == "finished"
        assert job.finished_at is not None
        assert job.error_message == "no error"
        assert job.status_message == "done"
        assert job.current_step == 10
        assert job.total_steps == 10
        assert job.chunks_count == 5

    def test_update_job_not_found(self):
        # Should just log a warning and return
        self.repo.update_job(uuid4(), "status")

    def test_link_job_to_source(self):
        job_id = self.repo.create_job(content_source_id=None)
        cs_id = self._create_source()
        
        self.repo.link_job_to_source(job_id, cs_id, ingestion_type="manual")
        
        job = self.repo.get_by_id(job_id)
        assert job.content_source_id == cs_id
        assert job.ingestion_type == "manual"

    def test_link_job_not_found(self):
        self.repo.link_job_to_source(uuid4(), uuid4())

    def test_list_recent_jobs(self):
        self.repo.create_job(None)
        self.repo.create_job(None)
        jobs = self.repo.list_recent_jobs(limit=1)
        assert len(jobs) == 1

    def test_list_recent_jobs_by_subject(self):
        subject_id = uuid4()
        cs_id = self._create_source(subject_id=subject_id)
        self.repo.create_job(content_source_id=cs_id)
        
        jobs = self.repo.list_recent_jobs_by_subject(subject_id)
        assert len(jobs) == 1

    def test_list_by_content_source(self):
        cs_id = self._create_source()
        self.repo.create_job(content_source_id=cs_id)
        
        jobs = self.repo.list_by_content_source(cs_id)
        assert len(jobs) == 1
