import pytest
from uuid import uuid4
from unittest.mock import patch
from src.infrastructure.repositories.sql.knowledge_subject_repository import (
    KnowledgeSubjectSQLRepository,
)


@pytest.mark.Dependencies
class TestKnowledgeSubjectSQLRepository:
    def test_create_subject_success(self, sqlite_memory):
        repo = KnowledgeSubjectSQLRepository()
        sid = repo.create_subject(
            name="Test", external_ref="ref", description="desc", icon="icon"
        )
        assert sid is not None

        ks = repo.get_by_id(sid)
        assert ks.name == "Test"
        assert ks.external_ref == "ref"

    def test_create_subject_error(self, sqlite_memory):
        repo = KnowledgeSubjectSQLRepository()
        with patch("sqlalchemy.orm.Session.add", side_effect=Exception("DB Error")):
            with pytest.raises(Exception, match="DB Error"):
                repo.create_subject(name="Fail")

    def test_get_by_id_error(self, sqlite_memory):
        repo = KnowledgeSubjectSQLRepository()
        with patch("sqlalchemy.orm.Query.first", side_effect=Exception("DB Error")):
            with pytest.raises(Exception, match="DB Error"):
                repo.get_by_id(uuid4())

    def test_get_by_external_ref_success(self, sqlite_memory):
        repo = KnowledgeSubjectSQLRepository()
        repo.create_subject(name="A", external_ref="ref123")
        ks = repo.get_by_external_ref("ref123")
        assert ks.name == "A"
        assert repo.get_by_external_ref("none") is None

    def test_get_by_external_ref_error(self, sqlite_memory):
        repo = KnowledgeSubjectSQLRepository()
        with patch("sqlalchemy.orm.Query.first", side_effect=Exception("DB Error")):
            with pytest.raises(Exception, match="DB Error"):
                repo.get_by_external_ref("ref")

    def test_list_success(self, sqlite_memory):
        repo = KnowledgeSubjectSQLRepository()
        repo.create_subject(name="A")
        repo.create_subject(name="B")
        results = repo.list(limit=1)
        assert len(results) == 1

    def test_list_error(self, sqlite_memory):
        repo = KnowledgeSubjectSQLRepository()
        with patch("sqlalchemy.orm.Query.all", side_effect=Exception("DB Error")):
            with pytest.raises(Exception, match="DB Error"):
                repo.list()

    def test_update_success(self, sqlite_memory):
        repo = KnowledgeSubjectSQLRepository()
        sid = repo.create_subject(name="Old")
        repo.update(sid, name="New", description="d", external_ref="r")
        ks = repo.get_by_id(sid)
        assert ks.name == "New"
        assert ks.description == "d"
        assert ks.external_ref == "r"

    def test_update_not_found(self, sqlite_memory):
        repo = KnowledgeSubjectSQLRepository()
        # Should log warning and return
        repo.update(uuid4(), name="Fail")

    def test_update_error(self, sqlite_memory):
        repo = KnowledgeSubjectSQLRepository()
        sid = repo.create_subject(name="Test")
        with patch("sqlalchemy.orm.Session.commit", side_effect=Exception("DB Error")):
            with pytest.raises(Exception, match="DB Error"):
                repo.update(sid, name="Fail")

    def test_delete_success(self, sqlite_memory):
        repo = KnowledgeSubjectSQLRepository()
        sid = repo.create_subject(name="To Delete")
        count = repo.delete(sid)
        assert count == 1
        assert repo.get_by_id(sid) is None

    def test_delete_error(self, sqlite_memory):
        repo = KnowledgeSubjectSQLRepository()
        with patch("sqlalchemy.orm.Query.delete", side_effect=Exception("DB Error")):
            with pytest.raises(Exception, match="DB Error"):
                repo.delete(uuid4())

    def test_get_by_name_success(self, sqlite_memory):
        repo = KnowledgeSubjectSQLRepository()
        repo.create_subject(name="UniqueName")
        ks = repo.get_by_name("UniqueName")
        assert ks.name == "UniqueName"

    def test_get_by_name_error(self, sqlite_memory):
        repo = KnowledgeSubjectSQLRepository()
        with patch("sqlalchemy.orm.Query.first", side_effect=Exception("DB Error")):
            with pytest.raises(Exception, match="DB Error"):
                repo.get_by_name("UniqueName")
