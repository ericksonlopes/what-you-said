from uuid import uuid4

import pytest

import src.infrastructure.repositories.sql.chunk_index_repository as ch_mod
import src.infrastructure.repositories.sql.content_source_repository as cs_mod
import src.infrastructure.repositories.sql.ingestion_job_repository as ij_mod
import src.infrastructure.repositories.sql.knowledge_subject_repository as ks_mod


class RepositoryTestError(RuntimeError):
    """Raised by ErrSession to simulate repository errors in tests."""

    pass


class ErrSession:
    def get(self, *args, **kwargs):
        raise RepositoryTestError("get error")

    def query(self, *args, **kwargs):
        raise RepositoryTestError("query error")

    def add(self, *args, **kwargs):
        raise RepositoryTestError("add error")

    def commit(self, *args, **kwargs):
        raise RepositoryTestError("commit error")

    def rollback(self, *args, **kwargs):
        return None

    def close(self, *args, **kwargs):
        return None


class BadConnector:
    def __enter__(self):
        return ErrSession()

    def __exit__(self, *args, **kwargs):
        return False


@pytest.mark.usefixtures("sqlite_memory")
def test_repositories_handle_exceptions(monkeypatch):
    # Patch Connector in each module to force exceptions inside try blocks and trigger except handlers
    monkeypatch.setattr(ks_mod, "Connector", BadConnector)
    ks_repo = ks_mod.KnowledgeSubjectSQLRepository()
    with pytest.raises(RepositoryTestError):
        ks_repo.create_subject(name="x")
    with pytest.raises(RepositoryTestError):
        ks_repo.get_by_id(uuid4())
    with pytest.raises(RepositoryTestError):
        ks_repo.get_by_external_ref("x")
    with pytest.raises(RepositoryTestError):
        ks_repo.list()
    with pytest.raises(RepositoryTestError):
        ks_repo.update(uuid4(), name="n")
    with pytest.raises(RepositoryTestError):
        ks_repo.delete(uuid4())
    with pytest.raises(RepositoryTestError):
        ks_repo.get_by_name("name")

    monkeypatch.setattr(cs_mod, "Connector", BadConnector)
    cs_repo = cs_mod.ContentSourceSQLRepository()
    with pytest.raises(RepositoryTestError):
        cs_repo.create(subject_id=None, source_type="youtube", external_source="ex")
    with pytest.raises(RepositoryTestError):
        cs_repo.get_by_id(uuid4())
    with pytest.raises(RepositoryTestError):
        cs_repo.get_by_source_info("youtube", "ex")
    with pytest.raises(RepositoryTestError):
        cs_repo.list_by_subject(uuid4())
    with pytest.raises(RepositoryTestError):
        cs_repo.update_status(uuid4(), "processing")
    with pytest.raises(RepositoryTestError):
        cs_repo.finish_ingestion(uuid4(), embedding_model="m", dimensions=1, chunks=1)

    monkeypatch.setattr(ij_mod, "Connector", BadConnector)
    ij_repo = ij_mod.IngestionJobSQLRepository()
    with pytest.raises(RepositoryTestError):
        ij_repo.create_job(content_source_id=None)
    with pytest.raises(RepositoryTestError):
        ij_repo.update_job(uuid4(), status="failed")
    with pytest.raises(RepositoryTestError):
        ij_repo.get_by_id(uuid4())
    with pytest.raises(RepositoryTestError):
        ij_repo.list_by_content_source(uuid4())

    monkeypatch.setattr(ch_mod, "Connector", BadConnector)
    ch_repo = ch_mod.ChunkIndexSQLRepository()
    with pytest.raises(RepositoryTestError):
        ch_repo.create_chunks(
            [
                {
                    "id": uuid4(),
                    "content_source_id": uuid4(),
                    "job_id": uuid4(),
                    "chunk_id": "x",
                }
            ]
        )
    with pytest.raises(RepositoryTestError):
        ch_repo.list_by_content_source(uuid4())
    with pytest.raises(RepositoryTestError):
        ch_repo.delete_by_content_source(uuid4())
    with pytest.raises(RepositoryTestError):
        ch_repo.search(query=None)
