import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from src.infrastructure.services.chunk_vector_service import ChunkVectorService
from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.entities.enums.source_type_enum_entity import SourceType
from src.domain.entities.enums.search_mode_enum import SearchMode
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel


@pytest.mark.ChunkVectorService
class TestChunkVectorService:
    @pytest.fixture
    def mock_repo(self):
        return MagicMock()

    @pytest.fixture
    def mock_rerank(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_repo, mock_rerank):
        return ChunkVectorService(repository=mock_repo, rerank_service=mock_rerank)

    def test_index_documents_empty(self, service):
        result = service.index_documents([])
        assert result == []

    def test_index_documents_success(self, service, mock_repo):
        entity = ChunkEntity(
            id=uuid4(),
            job_id=uuid4(),
            content_source_id=uuid4(),
            source_type=SourceType.YOUTUBE,
            external_source="vid1",
            subject_id=uuid4(),
            content="test content",
            embedding_model="test-emb",
        )
        mock_repo.create_documents.return_value = ["id1"]

        result = service.index_documents([entity])

        assert result == ["id1"]
        mock_repo.create_documents.assert_called_once()

    def test_retrieve_empty_query(self, service):
        with pytest.raises(ValueError, match="Query must be provided"):
            service.retrieve("", top_k=5)

    def test_retrieve_success_with_rerank(self, service, mock_repo, mock_rerank):
        common_args = {
            "job_id": uuid4(),
            "content_source_id": uuid4(),
            "source_type": "youtube",
            "external_source": "vid1",
            "subject_id": uuid4(),
            "embedding_model": "test-emb",
        }
        model1 = ChunkModel(id=uuid4(), content="text 1", score=0.5, **common_args)
        model2 = ChunkModel(id=uuid4(), content="text 2", score=0.4, **common_args)
        mock_repo.retriever.return_value = [model1, model2]

        # Mock rerank to swap order
        mock_rerank.rerank.return_value = [model2, model1]
        model2.score = 0.9
        model1.score = 0.8

        result = service.retrieve("query", top_k=2, re_rank=True)

        assert len(result) == 2
        assert result[0].content == "text 2"
        assert result[0].score == 0.9
        assert result[1].content == "text 1"
        assert result[1].score == 0.8

        mock_repo.retriever.assert_called_once_with(
            query="query",
            top_kn=2,
            filters=None,
            search_mode=SearchMode.SEMANTIC,
            re_rank=True,
        )
        mock_rerank.rerank.assert_called_once()

    def test_retrieve_no_rerank_service(self, mock_repo):
        service = ChunkVectorService(repository=mock_repo, rerank_service=None)
        common_args = {
            "job_id": uuid4(),
            "content_source_id": uuid4(),
            "source_type": "youtube",
            "external_source": "vid1",
            "subject_id": uuid4(),
            "embedding_model": "test-emb",
        }
        model = ChunkModel(id=uuid4(), content="text", score=0.7, **common_args)
        mock_repo.retriever.return_value = [model]

        result = service.retrieve("query", top_k=1, re_rank=True)

        assert len(result) == 1
        assert result[0].score == 0.7

    def test_list_by_source(self, service, mock_repo):
        common_args = {
            "job_id": uuid4(),
            "content_source_id": uuid4(),
            "source_type": "youtube",
            "external_source": "vid1",
            "subject_id": uuid4(),
            "embedding_model": "test-emb",
        }
        model = ChunkModel(id=uuid4(), content="text", **common_args)
        mock_repo.list_chunks.return_value = [model]

        result = service.list_by_source(filters={"source_id": "123"})

        assert len(result) == 1
        mock_repo.list_chunks.assert_called_once_with(filters={"source_id": "123"})

    def test_delete(self, service, mock_repo):
        mock_repo.delete.return_value = 5
        result = service.delete(filters={"source": "abc"})
        assert result == 5
        mock_repo.delete.assert_called_once_with(filters={"source": "abc"})

    def test_delete_by_id(self, service, mock_repo):
        cid = uuid4()
        mock_repo.delete.return_value = 1
        result = service.delete_by_id(cid)
        assert result == 1
        mock_repo.delete.assert_called_once_with(filters={"id": cid})
