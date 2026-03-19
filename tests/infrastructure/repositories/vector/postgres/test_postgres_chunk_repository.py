import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel
from src.infrastructure.repositories.vector.postgres.chunk_repository import (
    ChunkPostgresRepository,
)


@pytest.fixture
def mock_embedding_service():
    return MagicMock()


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.add_documents.return_value = []
    store.similarity_search_with_score.return_value = []
    store.delete.return_value = None
    return store


@pytest.fixture
def repo(mock_embedding_service, mock_vector_store):
    with patch(
        "src.infrastructure.repositories.vector.postgres.postgres_vector.PostgresVector"
    ) as mock_ctx_cls:
        mock_ctx = mock_ctx_cls.return_value
        mock_ctx.__enter__.return_value = mock_vector_store

        repository = ChunkPostgresRepository(
            embedding_service=mock_embedding_service, collection_name="test_collection"
        )
        return repository


def test_create_documents_success(repo, mock_vector_store):
    doc = ChunkModel(
        job_id=uuid4(),
        content_source_id=uuid4(),
        source_type="YOUTUBE",
        external_source="v1",
        content="hello postgres",
        embedding_model="test-model",
    )

    mock_vector_store.add_documents.return_value = [str(doc.id)]

    created_ids = repo.create_documents([doc])

    assert len(created_ids) == 1
    assert created_ids[0] == str(doc.id)
    assert mock_vector_store.add_documents.called


def test_retriever_returns_models(repo, mock_vector_store):
    from langchain_core.documents import Document

    jid = str(uuid4())
    csid = str(uuid4())

    mock_doc = Document(
        page_content="result",
        metadata={
            "job_id": jid,
            "content_source_id": csid,
            "source_type": "YOUTUBE",
            "external_source": "v1",
            "embedding_model": "test-model",
            "content": "result",
        },
    )

    mock_vector_store.similarity_search_with_score.return_value = [(mock_doc, 0.95)]

    results = repo.retriever(query="test", top_kn=1)

    assert len(results) == 1
    assert isinstance(results[0], ChunkModel)
    assert results[0].content == "result"
    assert str(results[0].job_id) == jid
    assert str(results[0].content_source_id) == csid
    assert results[0].score == 0.95
    assert mock_vector_store.similarity_search_with_score.called


def test_is_ready(repo):
    repo.vector_store_ctx._ensure_initialized = MagicMock()
    assert repo.is_ready() is True
    assert repo.vector_store_ctx._ensure_initialized.called


def test_delete_by_id(repo, mock_vector_store):
    chunk_id = str(uuid4())
    repo.delete(filters={"id": chunk_id})

    mock_vector_store.delete.assert_called_with(ids=[chunk_id])
