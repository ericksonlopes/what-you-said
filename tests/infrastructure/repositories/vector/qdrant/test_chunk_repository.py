from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pydantic_core
import pytest
from qdrant_client.http import models as rest

from src.domain.entities.enums.search_mode_enum import SearchMode
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel
from src.infrastructure.repositories.vector.qdrant.chunk_repository import (
    ChunkQdrantRepository,
)


@pytest.mark.ChunkQdrantRepository
class TestChunkQdrantRepository:
    @pytest.fixture
    def mock_connector(self):
        connector = MagicMock()
        mock_client = MagicMock()
        connector.__enter__.return_value = mock_client
        return connector

    @pytest.fixture
    def mock_embedding_service(self):
        service = MagicMock()
        service.model_loader_service.dimensions = 1536
        service.embed_query.return_value = [0.1] * 1536
        return service

    @pytest.fixture
    def repo(self, mock_connector, mock_embedding_service):
        with patch.object(ChunkQdrantRepository, "_ensure_collection_exists"):
            return ChunkQdrantRepository(
                connector=mock_connector,
                embedding_service=mock_embedding_service,
                collection_name="test_collection",
            )

    def test_ensure_collection_exists_creates_if_not_present(
        self, mock_connector, mock_embedding_service
    ):
        mock_client = mock_connector.__enter__.return_value
        mock_client.collection_exists.return_value = False

        repo = ChunkQdrantRepository(
            connector=mock_connector,
            embedding_service=mock_embedding_service,
            collection_name="test_collection",
        )

        repo._ensure_collection_exists()

        mock_client.create_collection.assert_called_once()
        mock_client.create_payload_index.assert_called_once()

    def test_ensure_collection_exists_skips_if_present(
        self, mock_connector, mock_embedding_service
    ):
        mock_client = mock_connector.__enter__.return_value
        mock_client.collection_exists.return_value = True

        repo = ChunkQdrantRepository(
            connector=mock_connector,
            embedding_service=mock_embedding_service,
            collection_name="test_collection",
        )

        repo._ensure_collection_exists()

        mock_client.create_collection.assert_not_called()

    def test_create_documents_success(
        self, repo, mock_connector, mock_embedding_service
    ):
        doc = ChunkModel(
            id=uuid4(),
            job_id=uuid4(),
            content_source_id=uuid4(),
            source_type="YOUTUBE",
            content="test content",
            created_at=datetime.now(timezone.utc),
        )
        mock_client = mock_connector.__enter__.return_value

        ids = repo.create_documents([doc])

        assert ids == [str(doc.id)]
        mock_client.upsert.assert_called_once()
        mock_embedding_service.embed_query.assert_called_with("test content")

    def test_create_documents_skips_empty_content(self, repo, mock_connector):
        doc = ChunkModel(
            id=uuid4(),
            job_id=uuid4(),
            content_source_id=uuid4(),
            source_type="YOUTUBE",
            content="",
            created_at=datetime.now(timezone.utc),
        )
        mock_client = mock_connector.__enter__.return_value

        ids = repo.create_documents([doc])

        assert ids == [str(doc.id)]
        mock_client.upsert.assert_called_once()
        _, kwargs = mock_client.upsert.call_args
        assert len(kwargs["points"]) == 0

    def test_create_documents_exception(self, repo, mock_connector):
        mock_client = mock_connector.__enter__.return_value
        mock_client.upsert.side_effect = Exception("Qdrant error")

        doc = ChunkModel(
            id=uuid4(),
            job_id=uuid4(),
            content_source_id=uuid4(),
            content="test",
            source_type="T",
            created_at=datetime.now(),
        )

        with pytest.raises(Exception, match="Qdrant error"):
            repo.create_documents([doc])

    def test_semantic_search(self, repo, mock_connector):
        mock_client = mock_connector.__enter__.return_value
        mock_hit = MagicMock()
        mock_hit.score = 0.9
        mock_hit.payload = {
            "id": str(uuid4()),
            "job_id": str(uuid4()),
            "content_source_id": str(uuid4()),
            "content": "found",
            "source_type": "T",
            "created_at": datetime.now().isoformat(),
        }
        mock_response = MagicMock()
        mock_response.points = [mock_hit]
        mock_client.query_points.return_value = mock_response

        results = repo.retriever("query", search_mode=SearchMode.SEMANTIC)

        assert len(results) == 1
        assert results[0].content == "found"
        mock_client.query_points.assert_called_once()

    def test_bm25_search_success(self, repo, mock_connector):
        mock_client = mock_connector.__enter__.return_value
        mock_hit = MagicMock()
        mock_hit.payload = {
            "id": str(uuid4()),
            "job_id": str(uuid4()),
            "content_source_id": str(uuid4()),
            "content": "bm25",
            "source_type": "T",
        }
        mock_response = MagicMock()
        mock_response.points = [mock_hit]
        mock_client.query_points.return_value = mock_response

        results = repo.retriever("query", search_mode=SearchMode.BM25)

        assert len(results) == 1
        assert results[0].content == "bm25"

    def test_bm25_search_fallback_to_scroll(self, repo, mock_connector):
        mock_client = mock_connector.__enter__.return_value
        mock_client.query_points.side_effect = Exception("New API not available")

        mock_hit = MagicMock()
        mock_hit.payload = {
            "id": str(uuid4()),
            "job_id": str(uuid4()),
            "content_source_id": str(uuid4()),
            "content": "scroll",
            "source_type": "T",
        }
        mock_client.scroll.return_value = ([mock_hit], None)

        results = repo.retriever("query", search_mode=SearchMode.BM25)

        assert len(results) == 1
        assert results[0].content == "scroll"
        mock_client.scroll.assert_called_once()

    def test_hybrid_search(self, repo, mock_connector):
        mock_client = mock_connector.__enter__.return_value

        id1 = uuid4()
        jid1 = uuid4()
        csid1 = uuid4()
        hit1 = MagicMock(score=0.9)
        hit1.payload = {
            "id": str(id1),
            "job_id": str(jid1),
            "content_source_id": str(csid1),
            "content": "res1",
            "source_type": "T",
        }

        id2 = uuid4()
        jid2 = uuid4()
        csid2 = uuid4()
        hit2 = MagicMock()
        hit2.payload = {
            "id": str(id2),
            "job_id": str(jid2),
            "content_source_id": str(csid2),
            "content": "res2",
            "source_type": "T",
        }

        mock_response_semantic = MagicMock(points=[hit1])
        mock_response_bm25 = MagicMock(points=[hit2])

        mock_client.query_points.side_effect = [
            mock_response_semantic,
            mock_response_bm25,
        ]

        results = repo.retriever("query", search_mode=SearchMode.HYBRID)

        assert len(results) == 2

    def test_delete_with_filters(self, repo, mock_connector):
        mock_client = mock_connector.__enter__.return_value
        count = repo.delete(filters={"content_source_id": str(uuid4())})
        assert count == 1
        mock_client.delete.assert_called_once()

    def test_delete_no_filters_returns_zero(self, repo, mock_connector):
        count = repo.delete(filters=None)
        assert count == 0

    def test_list_chunks(self, repo, mock_connector):
        mock_client = mock_connector.__enter__.return_value
        mock_hit = MagicMock()
        mock_hit.payload = {
            "id": str(uuid4()),
            "job_id": str(uuid4()),
            "content_source_id": str(uuid4()),
            "content": "chunk",
            "source_type": "T",
            "index": 1,
        }
        mock_client.scroll.return_value = ([mock_hit], None)

        chunks = repo.list_chunks(filters={"subject_id": str(uuid4())})

        assert len(chunks) == 1
        assert chunks[0].content == "chunk"

    def test_is_ready(self, repo, mock_connector):
        mock_connector.is_ready.return_value = True
        assert repo.is_ready() is True

        mock_connector.is_ready.return_value = False
        assert repo.is_ready() is False

    def test_convert_filters_none(self, repo):
        assert repo._convert_filters(None) is None

    def test_convert_filters_already_qdrant_filter(self, repo):
        f = rest.Filter(must=[])
        assert repo._convert_filters(f) == f

    def test_convert_filters_id(self, repo):
        id_val = uuid4()
        f = repo._convert_filters({"id": id_val})
        assert isinstance(f.must[0], rest.HasIdCondition)
        assert f.must[0].has_id == [str(id_val)]

    def test_transform_hits_invalid_date(self, repo):
        hit = MagicMock()
        hit.payload = {
            "id": str(uuid4()),
            "job_id": str(uuid4()),
            "content_source_id": str(uuid4()),
            "content": "test",
            "source_type": "T",
            "created_at": "not-a-date",
        }
        hits = [hit]
        # This will still raise ValidationError because ChunkModel expects valid datetime
        with pytest.raises(pydantic_core._pydantic_core.ValidationError):
            repo._transform_hits(hits)

    def test_bm25_search_with_existing_filters(self, repo, mock_connector):
        mock_client = mock_connector.__enter__.return_value
        mock_client.query_points.return_value = MagicMock(points=[])

        existing_filters = rest.Filter(
            must=[
                rest.FieldCondition(
                    key="subject_id", match=rest.MatchValue(value="123")
                )
            ],
            should=[
                rest.FieldCondition(key="extra", match=rest.MatchValue(value="val"))
            ],
            must_not=[
                rest.FieldCondition(key="bad", match=rest.MatchValue(value="val"))
            ],
        )

        repo._bm25_search("query", 5, existing_filters)

        _, kwargs = mock_client.query_points.call_args
        sent_filter = kwargs["query_filter"]
        assert len(sent_filter.must) == 2
        assert len(sent_filter.should) == 1
        assert len(sent_filter.must_not) == 1
