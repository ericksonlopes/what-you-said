import pytest
from uuid import uuid4
from unittest.mock import patch
from src.infrastructure.repositories.sql.content_source_repository import (
    ContentSourceSQLRepository,
)


@pytest.mark.Dependencies
class TestContentSourceSQLRepository:
    def test_create_success(self, sqlite_memory):
        repo = ContentSourceSQLRepository()
        sid = uuid4()
        cid = repo.create(
            subject_id=sid,
            source_type="youtube",
            external_source="vid1",
            title="Title",
            embedding_model="emb",
            dimensions=384,
        )
        assert cid is not None

        # Verify
        cs = repo.get_by_id(cid)
        assert cs.title == "Title"
        assert cs.source_type == "youtube"

    def test_get_by_id_error(self, sqlite_memory):
        repo = ContentSourceSQLRepository()
        with patch("sqlalchemy.orm.Session.get", side_effect=Exception("DB Error")):
            with pytest.raises(Exception, match="DB Error"):
                repo.get_by_id(uuid4())

    def test_get_by_source_info(self, sqlite_memory):
        repo = ContentSourceSQLRepository()
        sid = uuid4()
        repo.create(sid, "pdf", "file.pdf", title="Doc")

        # Success with subject_id
        results = repo.get_by_source_info("pdf", "file.pdf", sid)
        assert len(results) == 1
        assert results[0].title == "Doc"

        # Success without subject_id
        results = repo.get_by_source_info("pdf", "file.pdf")
        assert len(results) == 1

        # Not found
        results = repo.get_by_source_info("pdf", "other.pdf")
        assert len(results) == 0

    def test_list_by_subject(self, sqlite_memory):
        repo = ContentSourceSQLRepository()
        sid = uuid4()
        repo.create(sid, "pdf", "1.pdf")
        repo.create(sid, "pdf", "2.pdf")
        repo.create(uuid4(), "pdf", "3.pdf")

        results = repo.list_by_subject(sid, limit=1, offset=0)
        assert len(results) == 1

        results = repo.list_by_subject(sid)
        assert len(results) == 2

    def test_list_all(self, sqlite_memory):
        repo = ContentSourceSQLRepository()
        repo.create(uuid4(), "pdf", "1.pdf")
        repo.create(uuid4(), "pdf", "2.pdf")

        results = repo.list(limit=1)
        assert len(results) == 1

        results = repo.list(offset=1)
        assert len(results) == 1

    def test_count_by_subject(self, sqlite_memory):
        repo = ContentSourceSQLRepository()
        sid = uuid4()
        repo.create(sid, "pdf", "1.pdf")
        repo.create(sid, "pdf", "2.pdf")

        assert repo.count_by_subject(sid) == 2
        assert repo.count_by_subject(uuid4()) == 0

    def test_update_status(self, sqlite_memory):
        repo = ContentSourceSQLRepository()
        cid = repo.create(uuid4(), "pdf", "1.pdf", processing_status="pending")

        repo.update_status(cid, "done")
        assert repo.get_by_id(cid).processing_status == "done"

        # Not found
        repo.update_status(uuid4(), "error")

    def test_update_title(self, sqlite_memory):
        repo = ContentSourceSQLRepository()
        cid = repo.create(uuid4(), "pdf", "1.pdf", title="Old")

        repo.update_title(cid, "New")
        assert repo.get_by_id(cid).title == "New"

        # Not found
        repo.update_title(uuid4(), "Fail")

    def test_finish_ingestion(self, sqlite_memory):
        repo = ContentSourceSQLRepository()
        cid = repo.create(uuid4(), "pdf", "1.pdf", processing_status="pending")

        repo.finish_ingestion(cid, "model-x", 512, 100)
        cs = repo.get_by_id(cid)
        assert cs.processing_status == "done"
        assert cs.embedding_model == "model-x"
        assert cs.chunks == 100

        # Not found
        repo.finish_ingestion(uuid4(), "m", 1, 1)

    def test_create_error(self, sqlite_memory):
        repo = ContentSourceSQLRepository()
        with patch("sqlalchemy.orm.Session.add", side_effect=Exception("Create Error")):
            with pytest.raises(Exception, match="Create Error"):
                repo.create(uuid4(), "type", "ext")

    def test_get_by_source_info_error(self, sqlite_memory):
        repo = ContentSourceSQLRepository()
        with patch("sqlalchemy.orm.Query.all", side_effect=Exception("Query Error")):
            with pytest.raises(Exception, match="Query Error"):
                repo.get_by_source_info("type", "ext")

    def test_list_by_subject_error(self, sqlite_memory):
        repo = ContentSourceSQLRepository()
        with patch("sqlalchemy.orm.Query.all", side_effect=Exception("List Error")):
            with pytest.raises(Exception, match="List Error"):
                repo.list_by_subject(uuid4())

    def test_list_all_error(self, sqlite_memory):
        repo = ContentSourceSQLRepository()
        with patch("sqlalchemy.orm.Query.all", side_effect=Exception("All Error")):
            with pytest.raises(Exception, match="All Error"):
                repo.list()

    def test_count_by_subject_error(self, sqlite_memory):
        repo = ContentSourceSQLRepository()
        with patch("sqlalchemy.orm.Query.count", side_effect=Exception("Count Error")):
            with pytest.raises(Exception, match="Count Error"):
                repo.count_by_subject(uuid4())

    def test_update_status_error(self, sqlite_memory):
        repo = ContentSourceSQLRepository()
        cid = repo.create(uuid4(), "pdf", "1.pdf")
        with patch(
            "sqlalchemy.orm.Session.commit", side_effect=Exception("Update Error")
        ):
            with pytest.raises(Exception, match="Update Error"):
                repo.update_status(cid, "status")

    def test_update_title_error(self, sqlite_memory):
        repo = ContentSourceSQLRepository()
        cid = repo.create(uuid4(), "pdf", "1.pdf")
        with patch(
            "sqlalchemy.orm.Session.commit", side_effect=Exception("Update Error")
        ):
            with pytest.raises(Exception, match="Update Error"):
                repo.update_title(cid, "title")

    def test_finish_ingestion_error(self, sqlite_memory):
        repo = ContentSourceSQLRepository()
        cid = repo.create(uuid4(), "pdf", "1.pdf")
        with patch(
            "sqlalchemy.orm.Session.commit", side_effect=Exception("Finish Error")
        ):
            with pytest.raises(Exception, match="Finish Error"):
                repo.finish_ingestion(cid, "m", 1, 1)
