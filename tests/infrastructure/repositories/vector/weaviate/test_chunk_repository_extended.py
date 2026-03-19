import pytest
import sys
from unittest.mock import MagicMock, patch
from uuid import uuid4
from types import SimpleNamespace

# Mock weaviate and its complex nested structure
mock_weaviate = MagicMock()
mock_filter = MagicMock()
mock_weaviate.collections.classes.filters.Filter = mock_filter
sys.modules["weaviate"] = mock_weaviate
sys.modules["weaviate.collections"] = MagicMock()
sys.modules["weaviate.collections.classes"] = MagicMock()
sys.modules["weaviate.collections.classes.filters"] = MagicMock()
sys.modules["weaviate.classes"] = MagicMock()
sys.modules["weaviate.classes.query"] = MagicMock()

from src.infrastructure.repositories.vector.weaviate.chunk_repository import (  # noqa: E402
    ChunkWeaviateRepository,
)
from src.domain.entities.enums.search_mode_enum import SearchMode  # noqa: E402


@pytest.mark.ChunkRepository
class TestChunkWeaviateRepository:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        client.__enter__.return_value = client
        return client

    @pytest.fixture
    def mock_emb(self):
        emb = MagicMock()
        emb.embed_query.return_value = [0.1] * 1536
        return emb

    @pytest.fixture
    def repo(self, mock_client, mock_emb):
        with patch(
            "src.infrastructure.repositories.vector.weaviate.weaviate_vector.WeaviateVector"
        ):
            return ChunkWeaviateRepository(mock_client, mock_emb, "TestCollection")

    def create_mock_weaviate_obj(self, content="text", score=0.9):
        obj = MagicMock()
        obj.uuid = str(uuid4())
        obj.properties = {
            "content": content,
            "job_id": str(uuid4()),
            "content_source_id": str(uuid4()),
            "source_type": "youtube",
            "external_source": "vid",
            "subject_id": str(uuid4()),
            "embedding_model": "emb",
        }
        obj.metadata = MagicMock()
        obj.metadata.score = score
        return obj

    def test_bm25_search(self, repo, mock_client):
        mock_col = MagicMock()
        mock_client.collections.get.return_value = mock_col

        mock_response = MagicMock()
        mock_response.objects = [self.create_mock_weaviate_obj("bm25 result")]
        mock_col.query.bm25.return_value = mock_response

        results = repo.retriever("keyword", search_mode=SearchMode.BM25)

        assert len(results) == 1
        assert results[0].content == "bm25 result"
        mock_col.query.bm25.assert_called_once()

    def test_hybrid_search(self, repo, mock_client):
        mock_col = MagicMock()
        mock_client.collections.get.return_value = mock_col

        mock_response = MagicMock()
        mock_response.objects = [self.create_mock_weaviate_obj("hybrid result")]
        mock_col.query.hybrid.return_value = mock_response

        results = repo.retriever("hybrid query", search_mode=SearchMode.HYBRID)

        assert len(results) == 1
        assert results[0].content == "hybrid result"
        mock_col.query.hybrid.assert_called_once()

    def test_delete_with_complex_filters(self, repo, mock_client, monkeypatch):
        # Mock the Filter class methods called in delete
        mock_f = MagicMock()
        monkeypatch.setattr("weaviate.collections.classes.filters.Filter", mock_f)

        mock_col = MagicMock()
        mock_client.collections.get.return_value = mock_col
        mock_col.data.delete_many.return_value = SimpleNamespace(matches=5)

        # Test multiple filters (triggers Filter.all_of)
        deleted = repo.delete(filters={"job_id": "j1", "type": "pdf"})
        assert deleted == 5
        mock_col.data.delete_many.assert_called_once()

    def test_is_ready(self, repo, mock_client):
        mock_client.is_ready.return_value = True
        assert repo.is_ready() is True

        mock_client.is_ready.return_value = False
        assert repo.is_ready() is False

    def test_create_documents_error_handling(self, repo):
        # Trigger an exception during model_dump or similar
        with pytest.raises(Exception):
            repo.create_documents([None])  # type: ignore
