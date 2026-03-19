import pytest
from uuid import uuid4
from unittest.mock import patch
from src.infrastructure.repositories.sql.chunk_index_repository import (
    ChunkIndexSQLRepository,
)
from src.infrastructure.repositories.sql.content_source_repository import (
    ContentSourceSQLRepository,
)


@pytest.mark.Dependencies
class TestChunkIndexSQLRepository:
    def test_create_chunks_success(self, sqlite_memory):
        repo = ChunkIndexSQLRepository()
        cs_repo = ContentSourceSQLRepository()

        sid = cs_repo.create(uuid4(), "youtube", "v1", chunks=0)
        jid = uuid4()

        chunk_data = [
            {
                "id": uuid4(),
                "content_source_id": sid,
                "job_id": jid,
                "content": "text 1",
                "chunk_id": "c1",
            },
            {
                "id": uuid4(),
                "content_source_id": sid,
                "job_id": jid,
                "content": "text 2",
                "chunk_id": "c2",
            },
        ]

        ids = repo.create_chunks(chunk_data)
        assert len(ids) == 2

        # Verify ContentSource count update
        cs = cs_repo.get_by_id(sid)
        assert cs.chunks == 2

    def test_create_chunks_error(self, sqlite_memory):
        repo = ChunkIndexSQLRepository()
        with pytest.raises(Exception):
            # Invalid data (None) to trigger exception
            repo.create_chunks([None])

    def test_list_by_content_source(self, sqlite_memory):
        repo = ChunkIndexSQLRepository()
        sid = uuid4()
        jid = uuid4()
        repo.create_chunks(
            [
                {
                    "content_source_id": sid,
                    "job_id": jid,
                    "content": "test",
                    "chunk_id": "c1",
                }
            ]
        )

        results = repo.list_by_content_source(sid, limit=1, offset=0)
        assert len(results) == 1

    def test_list_chunks(self, sqlite_memory):
        repo = ChunkIndexSQLRepository()
        sid = uuid4()
        jid = uuid4()
        repo.create_chunks(
            [
                {
                    "content_source_id": sid,
                    "job_id": jid,
                    "content": "matching",
                    "chunk_id": "c1",
                }
            ]
        )
        repo.create_chunks(
            [
                {
                    "content_source_id": uuid4(),
                    "job_id": uuid4(),
                    "content": "other",
                    "chunk_id": "c2",
                }
            ]
        )

        # Filter by source
        results = repo.list_chunks(source_id=sid)
        assert len(results) == 1

        # Search query
        results = repo.list_chunks(search_query="match")
        assert len(results) == 1
        assert results[0].content == "matching"

    def test_count_by_content_source(self, sqlite_memory):
        repo = ChunkIndexSQLRepository()
        sid = uuid4()
        jid = uuid4()
        repo.create_chunks(
            [
                {
                    "content_source_id": sid,
                    "job_id": jid,
                    "content": "a",
                    "chunk_id": "c1",
                }
            ]
        )
        assert repo.count_by_content_source(sid) == 1

    def test_delete_by_content_source(self, sqlite_memory):
        repo = ChunkIndexSQLRepository()
        cs_repo = ContentSourceSQLRepository()
        sid = cs_repo.create(uuid4(), "youtube", "v1", chunks=1)
        jid = uuid4()
        repo.create_chunks(
            [
                {
                    "content_source_id": sid,
                    "job_id": jid,
                    "content": "a",
                    "chunk_id": "c1",
                }
            ]
        )

        deleted = repo.delete_by_content_source(sid)
        assert deleted == 1
        assert cs_repo.get_by_id(sid).chunks == 0

    def test_search(self, sqlite_memory):
        repo = ChunkIndexSQLRepository()
        cs_repo = ContentSourceSQLRepository()
        sid = cs_repo.create(uuid4(), "youtube", "v1", title="Target Video")
        jid = uuid4()
        repo.create_chunks(
            [
                {
                    "content_source_id": sid,
                    "job_id": jid,
                    "content": "body",
                    "chunk_id": "cid-123",
                }
            ]
        )

        # Search by title (via join)
        results = repo.search("Target")
        assert len(results) == 1

        # Search by chunk_id
        results = repo.search("cid-123")
        assert len(results) == 1

        # Filters
        results = repo.search(None, filters={"content_source_id": sid})
        assert len(results) == 1

    def test_delete_chunk(self, sqlite_memory):
        repo = ChunkIndexSQLRepository()
        cs_repo = ContentSourceSQLRepository()
        sid = cs_repo.create(uuid4(), "youtube", "v1", chunks=1)
        jid = uuid4()
        cid = uuid4()
        repo.create_chunks(
            [
                {
                    "id": cid,
                    "content_source_id": sid,
                    "job_id": jid,
                    "content": "a",
                    "chunk_id": "c1",
                }
            ]
        )

        assert repo.delete_chunk(cid) is True

        # Verify chunk is gone
        assert repo.get_by_id(cid) is None

    def test_update_chunk(self, sqlite_memory):
        repo = ChunkIndexSQLRepository()
        cid = uuid4()
        sid = uuid4()
        jid = uuid4()
        repo.create_chunks(
            [
                {
                    "id": cid,
                    "content_source_id": sid,
                    "job_id": jid,
                    "content": "old",
                    "chunk_id": "c1",
                }
            ]
        )

        assert repo.update_chunk(cid, "new") is True
        assert repo.get_by_id(cid).content == "new"

        # Not found
        assert repo.update_chunk(uuid4(), "fail") is False

    def test_get_by_id_error(self, sqlite_memory):
        repo = ChunkIndexSQLRepository()
        with patch("sqlalchemy.orm.Query.first", side_effect=Exception("Error")):
            assert repo.get_by_id(uuid4()) is None

    def test_delete_by_content_source_error(self, sqlite_memory):
        repo = ChunkIndexSQLRepository()
        with patch(
            "sqlalchemy.orm.Session.commit", side_effect=Exception("Commit Error")
        ):
            with pytest.raises(Exception, match="Commit Error"):
                repo.delete_by_content_source(uuid4())

    def test_list_by_content_source_error(self, sqlite_memory):
        repo = ChunkIndexSQLRepository()
        with patch("sqlalchemy.orm.Query.all", side_effect=Exception("List Error")):
            with pytest.raises(Exception, match="List Error"):
                repo.list_by_content_source(uuid4())

    def test_list_chunks_error(self, sqlite_memory):
        repo = ChunkIndexSQLRepository()
        with patch("sqlalchemy.orm.Query.all", side_effect=Exception("List Error")):
            with pytest.raises(Exception, match="List Error"):
                repo.list_chunks()

    def test_delete_chunk_error(self, sqlite_memory):
        repo = ChunkIndexSQLRepository()
        cid = uuid4()
        sid = uuid4()
        jid = uuid4()
        repo.create_chunks(
            [
                {
                    "id": cid,
                    "content_source_id": sid,
                    "job_id": jid,
                    "content": "a",
                    "chunk_id": "c1",
                }
            ]
        )
        with patch(
            "sqlalchemy.orm.Session.commit", side_effect=Exception("Delete Error")
        ):
            with pytest.raises(Exception, match="Delete Error"):
                repo.delete_chunk(cid)

    def test_update_chunk_error(self, sqlite_memory):
        repo = ChunkIndexSQLRepository()
        cid = uuid4()
        sid = uuid4()
        jid = uuid4()
        repo.create_chunks(
            [
                {
                    "id": cid,
                    "content_source_id": sid,
                    "job_id": jid,
                    "content": "old",
                    "chunk_id": "c1",
                }
            ]
        )
        with patch(
            "sqlalchemy.orm.Session.commit", side_effect=Exception("Update Error")
        ):
            with pytest.raises(Exception, match="Update Error"):
                repo.update_chunk(cid, "new")
