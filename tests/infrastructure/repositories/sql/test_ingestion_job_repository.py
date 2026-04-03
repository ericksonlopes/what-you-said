from uuid import uuid4, UUID
import pytest
from src.infrastructure.repositories.sql.ingestion_job_repository import (
    IngestionJobSQLRepository,
)
from src.infrastructure.repositories.sql.content_source_repository import (
    ContentSourceSQLRepository,
)
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
            language="en",
        )

    def test_create_job_success(self):
        cs_id = self._create_source()
        job_id = self.repo.create_job(content_source_id=cs_id, status="started")
        assert isinstance(job_id, UUID)

        job = self.repo.get_by_id(job_id)
        assert job.status == "started"
        assert job.content_source_id == cs_id

    def test_create_job_error(self):
        # Mock session to raise an error during add
        from unittest.mock import patch
        with patch("src.infrastructure.repositories.sql.ingestion_job_repository.Connector") as mock_connector:
            mock_session = mock_connector.return_value.__enter__.return_value
            mock_session.add.side_effect = Exception("DB Error")
            with pytest.raises(Exception):
                self.repo.create_job(content_source_id=None)

    def test_update_job_success(self):
        job_id = self.repo.create_job(content_source_id=None)
        self.repo.update_job(
            job_id=job_id,
            status="finished",
            error_message="no error",
            status_message="done",
            current_step=10,
            total_steps=10,
            chunks_count=5,
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

    def test_get_by_id_error(self):
        from unittest.mock import patch

        with patch("sqlalchemy.orm.Query.first", side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                self.repo.get_by_id(uuid4())

    def test_list_recent_jobs_error(self):
        from unittest.mock import patch

        with patch("sqlalchemy.orm.Query.all", side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                self.repo.list_recent_jobs()

    def test_list_recent_jobs_by_subject_error(self):
        from unittest.mock import patch

        with patch("sqlalchemy.orm.Query.all", side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                self.repo.list_recent_jobs_by_subject(uuid4())

    def test_list_by_content_source_error(self):
        from unittest.mock import patch

        with patch("sqlalchemy.orm.Query.all", side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                self.repo.list_by_content_source(uuid4())

    def test_link_job_to_source_error(self):
        from unittest.mock import patch

        # Trigger error during commit
        job_id = self.repo.create_job(None)
        with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                self.repo.link_job_to_source(job_id, uuid4())

    def test_update_job_error(self):
        from unittest.mock import patch

        job_id = self.repo.create_job(None)
        with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                self.repo.update_job(job_id, "finished")

    def test_list_jobs_filtering_and_search(self):
        # Create various jobs
        self.repo.create_job(None, status="started", source_title="alpha")
        self.repo.create_job(None, status="processing", source_title="beta")
        self.repo.create_job(None, status="finished", source_title="gamma")
        self.repo.create_job(None, status="failed", source_title="delta")
        jid_dup = self.repo.create_job(None, status="failed", source_title="epsilon")
        self.repo.update_job(
            jid_dup, status="failed", error_message="Duplicate content detected"
        )
        self.repo.create_job(None, status="cancelled", source_title="zeta")

        # Test status filters
        assert len(self.repo.list_jobs(status="processing")) == 2  # started, processing
        assert len(self.repo.list_jobs(status="completed")) == 1  # finished
        assert (
            len(self.repo.list_jobs(status="failed")) == 1
        )  # delta (epsilon is duplicate)
        assert (
            len(self.repo.list_jobs(status="cancelled")) == 2
        )  # zeta, epsilon (duplicate)
        assert len(self.repo.list_jobs(status="started")) == 1

        # Test search
        assert len(self.repo.list_jobs(search="alpha")) == 1
        assert len(self.repo.list_jobs(search="beta")) == 1
        assert len(self.repo.list_jobs(search="nonexistent")) == 0

        # Test pagination
        assert len(self.repo.list_jobs(limit=2)) == 2
        assert len(self.repo.list_jobs(limit=2, offset=4)) == 2

    def test_count_jobs(self):
        self.repo.create_job(None, status="finished", source_title="One")
        self.repo.create_job(None, status="failed", source_title="Two")

        assert self.repo.count_jobs() == 2
        assert self.repo.count_jobs(status="completed") == 1
        assert self.repo.count_jobs(search="One") == 1

    def test_get_status_counts(self):
        self.repo.create_job(None, status="started")  # processing
        self.repo.create_job(None, status="finished")  # completed
        self.repo.create_job(None, status="failed")  # failed
        jid = self.repo.create_job(None, status="failed")
        self.repo.update_job(
            jid, status="failed", error_message="Duplicate"
        )  # cancelled
        self.repo.create_job(None, status="cancelled")  # cancelled

        counts = self.repo.get_status_counts()
        assert counts["total"] == 5
        assert counts["processing"] == 1
        assert counts["completed"] == 1
        assert counts["failed"] == 1
        assert counts["cancelled"] == 2

    def test_get_status_counts_with_search(self):
        self.repo.create_job(None, status="finished", source_title="Match")
        self.repo.create_job(None, status="finished", source_title="Other")

        counts = self.repo.get_status_counts(search="Match")
        assert counts["total"] == 1
        assert counts["completed"] == 1

    def test_count_jobs_error(self):
        from unittest.mock import patch

        with patch("sqlalchemy.orm.Query.count", side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                self.repo.count_jobs()

    def test_get_status_counts_error(self):
        from unittest.mock import patch

        with patch("sqlalchemy.orm.Query.count", side_effect=Exception("DB error")):
            with pytest.raises(Exception, match="DB error"):
                self.repo.get_status_counts()
