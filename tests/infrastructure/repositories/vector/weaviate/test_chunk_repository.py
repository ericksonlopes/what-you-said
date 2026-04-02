import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone
from src.infrastructure.repositories.vector.weaviate.chunk_repository import (
    ChunkWeaviateRepository,
)
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel
from src.domain.entities.enums.search_mode_enum import SearchMode


@pytest.mark.ChunkWeaviateRepository
class TestChunkWeaviateRepository:
    @pytest.fixture
    def mock_weaviate_client(self):
        client = MagicMock()
        client.__enter__.return_value = client
        return client

    @pytest.fixture
    def mock_embedding_service(self):
        return MagicMock()

    @pytest.fixture
    def repo(self, mock_weaviate_client, mock_embedding_service):
        with patch(
            "src.infrastructure.repositories.vector.weaviate.weaviate_vector.WeaviateVector"
        ):
            return ChunkWeaviateRepository(
                weaviate_client=mock_weaviate_client,
                embedding_service=mock_embedding_service,
                collection_name="TestCollection",
            )

    def test_create_documents_success(self, repo):
        job_id = uuid4()
        cs_id = uuid4()
        doc = ChunkModel(
            id=uuid4(),
            content="test content",
            job_id=job_id,
            content_source_id=cs_id,
            source_type="youtube",
            external_source="vid1",
            subject_id=uuid4(),
            embedding_model="model",
            created_at=datetime.now(timezone.utc),
            extra={"key": "value"},
        )

        repo.vector_store.__enter__.return_value.add_texts.return_value = [str(doc.id)]

        ids = repo.create_documents([doc])
        assert ids == [str(doc.id)]
        assert repo.vector_store.__enter__.return_value.add_texts.called

    def test_create_documents_naive_datetime(self, repo):
        doc = ChunkModel(
            id=uuid4(),
            content="test",
            job_id=uuid4(),
            content_source_id=uuid4(),
            source_type="youtube",
            external_source="vid1",
            subject_id=uuid4(),
            embedding_model="model",
            created_at=datetime.now(),  # naive
        )
        repo.vector_store.__enter__.return_value.add_texts.return_value = [str(doc.id)]
        repo.create_documents([doc])

        _, kwargs = repo.vector_store.__enter__.return_value.add_texts.call_args
        assert kwargs["metadatas"][0]["created_at"].endswith("Z")

    def test_create_documents_error(self, repo):
        doc = ChunkModel(
            id=uuid4(),
            content="test",
            job_id=uuid4(),
            content_source_id=uuid4(),
            source_type="youtube",
            external_source="vid1",
            subject_id=uuid4(),
            embedding_model="model",
        )
        repo.vector_store.__enter__.return_value.add_texts.side_effect = Exception(
            "Weaviate error"
        )

        with pytest.raises(Exception, match="Weaviate error"):
            repo.create_documents([doc])

    def test_retriever_bm25(self, repo, mock_weaviate_client):
        mock_collection = MagicMock()
        mock_weaviate_client.collections.get.return_value = mock_collection

        mock_obj = MagicMock()
        mock_obj.uuid = uuid4()
        mock_obj.properties = {
            "content": "found",
            "job_id": str(uuid4()),
            "content_source_id": str(uuid4()),
            "source_type": "youtube",
            "external_source": "vid1",
            "subject_id": str(uuid4()),
            "embedding_model": "model",
        }
        mock_obj.metadata.score = 0.9

        mock_response = MagicMock()
        mock_response.objects = [mock_obj]
        mock_collection.query.bm25.return_value = mock_response

        results = repo.retriever("query", search_mode=SearchMode.BM25)
        assert len(results) == 1
        assert results[0].content == "found"
        assert results[0].score == pytest.approx(0.9)

    def test_retriever_hybrid(self, repo, mock_weaviate_client, mock_embedding_service):
        mock_collection = MagicMock()
        mock_weaviate_client.collections.get.return_value = mock_collection
        mock_embedding_service.embed_query.return_value = [0.1, 0.2]

        mock_obj = MagicMock()
        mock_obj.uuid = uuid4()
        mock_obj.properties = {
            "content": "hybrid",
            "job_id": str(uuid4()),
            "content_source_id": str(uuid4()),
            "source_type": "youtube",
            "external_source": "vid1",
            "subject_id": str(uuid4()),
            "embedding_model": "model",
        }
        mock_obj.metadata.score = None  # Force fallback to distance
        mock_obj.metadata.distance = 0.1

        mock_response = MagicMock()
        mock_response.objects = [mock_obj]
        mock_collection.query.hybrid.return_value = mock_response

        results = repo.retriever("query", search_mode=SearchMode.HYBRID)
        assert len(results) == 1
        # Match actual implementation logic: score is distance-based if present
        expected_score = float(1.0 / (1.0 + 0.1))
        assert results[0].score == pytest.approx(expected_score)

    def test_retriever_semantic_deduplication(self, repo):
        mock_doc1 = MagicMock()
        mock_doc1.page_content = "duplicate"
        mock_doc1.metadata = {
            "external_source": "src1",
            "job_id": str(uuid4()),
            "content_source_id": str(uuid4()),
            "source_type": "youtube",
            "subject_id": str(uuid4()),
            "embedding_model": "model",
        }
        mock_doc1.id = uuid4()  # Mapper looks for .id

        mock_doc2 = MagicMock()
        mock_doc2.page_content = "duplicate"
        mock_doc2.metadata = {
            "external_source": "src1",
            "job_id": str(uuid4()),
            "content_source_id": str(uuid4()),
            "source_type": "youtube",
            "subject_id": str(uuid4()),
            "embedding_model": "model",
        }
        mock_doc2.id = uuid4()

        repo.vector_store.__enter__.return_value.similarity_search_with_score.return_value = [
            (mock_doc1, 0.9),
            (mock_doc2, 0.8),
        ]

        results = repo.retriever("query", search_mode=SearchMode.SEMANTIC)
        assert len(results) == 1  # Deduplicated

    def test_retriever_filters_id(self, repo):
        # This tests the "if k == 'id'" branch
        with patch("weaviate.collections.classes.filters.Filter") as mock_filter:
            repo.retriever("query", filters={"id": "some-uuid", "other": "val"})
            assert mock_filter.by_id.called
            assert mock_filter.by_property.called
            assert mock_filter.all_of.called

    def test_delete_success(self, repo, mock_weaviate_client):
        mock_collection = MagicMock()
        mock_weaviate_client.collections.get.return_value = mock_collection
        mock_collection.data.delete_many.return_value = MagicMock(matches=5)

        count = repo.delete(filters={"job_id": "val"})
        assert count == 5

    def test_delete_no_filters(self, repo):
        assert repo.delete(filters=None) == 0
        assert repo.delete(filters={}) == 0

    def test_list_chunks_success(self, repo, mock_weaviate_client):
        mock_collection = MagicMock()
        mock_weaviate_client.collections.get.return_value = mock_collection

        mock_obj = MagicMock()
        mock_obj.uuid = uuid4()
        mock_obj.properties = {
            "content": "c1",
            "index": 1,
            "job_id": str(uuid4()),
            "content_source_id": str(uuid4()),
            "source_type": "youtube",
            "external_source": "vid1",
            "subject_id": str(uuid4()),
            "embedding_model": "model",
        }

        mock_response = MagicMock()
        mock_response.objects = [mock_obj]
        mock_collection.query.fetch_objects.return_value = mock_response

        chunks = repo.list_chunks(filters={"content_source_id": "val"})
        assert len(chunks) == 1
        assert chunks[0].content == "c1"

    def test_list_chunks_missing_uuid(self, repo, mock_weaviate_client):
        mock_collection = MagicMock()
        mock_weaviate_client.collections.get.return_value = mock_collection

        mock_obj = MagicMock(spec=[])  # No uuid attr
        mock_response = MagicMock()
        mock_response.objects = [mock_obj]
        mock_collection.query.fetch_objects.return_value = mock_response

        chunks = repo.list_chunks(filters={})
        assert len(chunks) == 0

    def test_is_ready(self, repo, mock_weaviate_client):
        mock_weaviate_client.is_ready.return_value = True
        assert repo.is_ready() is True
