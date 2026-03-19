import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from src.infrastructure.services.chunk_index_service import ChunkIndexService
from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.entities.enums.source_type_enum_entity import SourceType
from src.infrastructure.repositories.sql.models.chunk_index import ChunkIndexModel


@pytest.mark.ChunkIndexService
class TestChunkIndexService:
    @pytest.fixture
    def mock_repo(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_repo):
        return ChunkIndexService(repository=mock_repo)

    def create_mock_model(self, **kwargs):
        cid = kwargs.get("id", uuid4())
        model = ChunkIndexModel(
            id=cid,
            content_source_id=kwargs.get("content_source_id", uuid4()),
            job_id=kwargs.get("job_id", uuid4()),
            chunk_id=str(cid),
            content=kwargs.get("content", "text"),
            chars=len(kwargs.get("content", "text")),
            tokens_count=kwargs.get("tokens_count", 5),
            language=kwargs.get("language", "pt"),
            version_number=1,
            created_at=datetime.now(timezone.utc),
        )
        return model

    def test_create_chunks(self, service, mock_repo):
        sid = uuid4()
        jid = uuid4()
        cid = uuid4()
        entity = ChunkEntity(
            id=cid,
            job_id=jid,
            content_source_id=sid,
            source_type=SourceType.YOUTUBE,
            external_source="vid",
            subject_id=uuid4(),
            content="content",
            tokens_count=10,
            embedding_model="emb",
        )
        mock_repo.create_chunks.return_value = [cid]

        result = service.create_chunks([entity])

        assert result == [cid]
        mock_repo.create_chunks.assert_called_once()

    def test_list_by_content_source(self, service, mock_repo):
        sid = uuid4()
        mock_repo.list_by_content_source.return_value = [
            self.create_mock_model(content_source_id=sid)
        ]
        result = service.list_by_content_source(sid, limit=5, offset=0)
        assert len(result) == 1
        assert result[0].content_source_id == sid
        mock_repo.list_by_content_source.assert_called_once_with(
            content_source_id=sid, limit=5, offset=0
        )

    def test_count_by_content_source(self, service, mock_repo):
        sid = uuid4()
        mock_repo.count_by_content_source.return_value = 42
        assert service.count_by_content_source(sid) == 42
        mock_repo.count_by_content_source.assert_called_once_with(sid)

    def test_delete_by_content_source(self, service, mock_repo):
        sid = uuid4()
        mock_repo.delete_by_content_source.return_value = 10
        assert service.delete_by_content_source(sid) == 10
        mock_repo.delete_by_content_source.assert_called_once_with(
            content_source_id=sid
        )

    def test_search(self, service, mock_repo):
        mock_repo.search.return_value = [self.create_mock_model()]
        result = service.search("query", top_k=3, filters={"a": "b"})
        assert len(result) == 1
        mock_repo.search.assert_called_once_with(
            query="query", top_k=3, filters={"a": "b"}
        )

    def test_get_by_id(self, service, mock_repo):
        cid = uuid4()
        mock_repo.get_by_id.return_value = self.create_mock_model(id=cid)
        result = service.get_by_id(cid)
        assert result.id == cid

        mock_repo.get_by_id.return_value = None
        assert service.get_by_id(uuid4()) is None

    def test_list_chunks(self, service, mock_repo):
        sid = uuid4()
        mock_repo.list_chunks.return_value = [self.create_mock_model()]
        result = service.list_chunks(
            limit=10, offset=5, source_id=sid, search_query="q"
        )
        assert len(result) == 1
        mock_repo.list_chunks.assert_called_once_with(
            limit=10, offset=5, source_id=sid, search_query="q"
        )

    def test_delete_chunk(self, service, mock_repo):
        cid = uuid4()
        mock_repo.delete_chunk.return_value = True
        assert service.delete_chunk(cid) is True
        mock_repo.delete_chunk.assert_called_once_with(cid)

    def test_update_chunk(self, service, mock_repo):
        cid = uuid4()
        mock_repo.update_chunk.return_value = True
        assert service.update_chunk(cid, "new text") is True
        mock_repo.update_chunk.assert_called_once_with(cid, "new text")
