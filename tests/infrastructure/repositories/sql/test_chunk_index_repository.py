from uuid import uuid4, UUID
import pytest
from src.infrastructure.repositories.sql.chunk_index_repository import ChunkIndexSQLRepository
from src.infrastructure.repositories.sql.content_source_repository import ContentSourceSQLRepository
from src.domain.entities.enums.source_type_enum_entity import SourceType

from src.infrastructure.repositories.sql.ingestion_job_repository import IngestionJobSQLRepository

@pytest.mark.ChunkIndexRepository
@pytest.mark.usefixtures("sqlite_memory")
class TestChunkIndexSQLRepository:
    def setup_method(self):
        self.repo = ChunkIndexSQLRepository()
        self.cs_repo = ContentSourceSQLRepository()
        self.job_repo = IngestionJobSQLRepository()

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

    def _create_job(self, cs_id):
        return self.job_repo.create_job(
            content_source_id=cs_id,
            status="pending",
            embedding_model="test-model",
            pipeline_version="1.0"
        )

    def test_create_chunks_success(self):
        cs_id = self._create_source()
        job_id = self._create_job(cs_id)
        chunks = [
            {
                "id": uuid4(),
                "content_source_id": cs_id,
                "job_id": job_id,
                "chunk_id": "chunk-1",
                "content": "Hello world",
                "language": "en"
            },
            {
                "id": uuid4(),
                "content_source_id": cs_id,
                "job_id": job_id,
                "chunk_id": "chunk-2",
                "content": "Python is great",
                "language": "en"
            }
        ]
        ids = self.repo.create_chunks(chunks)
        assert len(ids) == 2
        assert isinstance(ids[0], UUID)

    def test_create_chunks_error(self):
        chunks = [{"invalid_key": "val"}]
        with pytest.raises(Exception):
            self.repo.create_chunks(chunks)

    def test_list_by_content_source(self):
        cs_id = self._create_source()
        job_id = self._create_job(cs_id)
        self.repo.create_chunks([{
            "id": uuid4(),
            "content_source_id": cs_id,
            "job_id": job_id,
            "chunk_id": "c1",
            "content": "c1 content"
        }])
        
        results = self.repo.list_by_content_source(cs_id, limit=10, offset=0)
        assert len(results) == 1
        assert results[0].chunk_id == "c1"

    def test_list_chunks_with_filters(self):
        cs_id = self._create_source()
        job_id = self._create_job(cs_id)
        self.repo.create_chunks([
            {"id": uuid4(), "content_source_id": cs_id, "job_id": job_id, "chunk_id": "c1", "content": "apple"},
            {"id": uuid4(), "content_source_id": cs_id, "job_id": job_id, "chunk_id": "c2", "content": "banana"}
        ])
        
        # Search by query
        res = self.repo.list_chunks(search_query="apple")
        assert len(res) == 1
        
        # Search by source_id
        res = self.repo.list_chunks(source_id=cs_id)
        assert len(res) == 2

    def test_count_by_content_source(self):
        cs_id = self._create_source()
        job_id = self._create_job(cs_id)
        self.repo.create_chunks([{"id": uuid4(), "content_source_id": cs_id, "job_id": job_id, "chunk_id": "c1", "content": "c1"}])
        assert self.repo.count_by_content_source(cs_id) == 1

    def test_delete_by_content_source(self):
        cs_id = self._create_source()
        job_id = self._create_job(cs_id)
        self.repo.create_chunks([{"id": uuid4(), "content_source_id": cs_id, "job_id": job_id, "chunk_id": "c1", "content": "c1"}])
        count = self.repo.delete_by_content_source(cs_id)
        assert count == 1
        assert self.repo.count_by_content_source(cs_id) == 0

    def test_search_complex(self):
        cs_id = self._create_source()
        job_id = self._create_job(cs_id)
        c_id = uuid4()
        self.repo.create_chunks([{"id": c_id, "content_source_id": cs_id, "job_id": job_id, "chunk_id": "special-chunk", "content": "content"}])
        
        # Search by chunk_id pattern
        res = self.repo.search(query="special")
        assert len(res) == 1
        
        # Search with filters - using id which is unambiguous or property of ChunkIndexModel
        res = self.repo.search(query=None, filters={"id": c_id})
        assert len(res) == 1

    def test_update_chunk(self):
        cs_id = self._create_source()
        job_id = self._create_job(cs_id)
        c_id = uuid4()
        self.repo.create_chunks([{"id": c_id, "content_source_id": cs_id, "job_id": job_id, "chunk_id": "c1", "content": "old"}])
        
        success = self.repo.update_chunk(c_id, "new content")
        assert success is True
        
        updated = self.repo.get_by_id(c_id)
        assert updated.content == "new content"
        assert updated.chars == len("new content")

    def test_update_chunk_not_found(self):
        assert self.repo.update_chunk(uuid4(), "content") is False

    def test_delete_chunk(self):
        cs_id = self._create_source()
        job_id = self._create_job(cs_id)
        c_id = uuid4()
        self.repo.create_chunks([{"id": c_id, "content_source_id": cs_id, "job_id": job_id, "chunk_id": "c1", "content": "c1"}])
        
        assert self.repo.delete_chunk(c_id) is True
        assert self.repo.get_by_id(c_id) is None

    def test_get_by_id_none(self):
        # We need to trigger the exception in get_by_id to hit the logger.error line
        # But get_by_id catches Exception and returns None.
        # It's hard to trigger without mocking session.query to raise.
        assert self.repo.get_by_id(uuid4()) is None
