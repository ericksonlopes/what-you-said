import pytest
import sys
from unittest.mock import MagicMock, patch
from uuid import uuid4

# Mock dependencies
mock_faiss_lib = MagicMock()
sys.modules["faiss"] = mock_faiss_lib
mock_langchain_faiss = MagicMock()
sys.modules["langchain_community.vectorstores"] = MagicMock()
sys.modules["langchain_community.vectorstores.faiss"] = mock_langchain_faiss

from src.infrastructure.repositories.vector.faiss.chunk_repository import (  # noqa: E402
    ChunkFAISSRepository,
)
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel  # noqa: E402
from src.domain.entities.enums.search_mode_enum import SearchMode  # noqa: E402


@pytest.mark.ChunkFAISSRepository
class TestChunkFAISSRepository:
    @pytest.fixture
    def mock_emb(self):
        return MagicMock()

    @pytest.fixture
    def temp_index_path(self, tmp_path):
        return str(tmp_path)

    def create_mock_chunk(self, **kwargs):
        cid = kwargs.get("id", uuid4())
        return ChunkModel(
            id=cid,
            content=kwargs.get("content", "text"),
            job_id=uuid4(),
            content_source_id=uuid4(),
            source_type="youtube",
            external_source="vid",
            subject_id=uuid4(),
            embedding_model="emb",
            extra=kwargs.get("extra", {}),
        )

    def test_init_new(self, mock_emb, temp_index_path):
        with patch("os.path.exists", return_value=False):
            repo = ChunkFAISSRepository(mock_emb, temp_index_path)
            assert repo._vector_store is None

    def test_init_load_existing(self, mock_emb, temp_index_path):
        with patch("os.path.exists", return_value=True):
            with patch(
                "langchain_community.vectorstores.FAISS.load_local"
            ) as mock_load:
                mock_store = MagicMock()
                mock_load.return_value = mock_store
                repo = ChunkFAISSRepository(mock_emb, temp_index_path)
                assert repo._vector_store == mock_store
                mock_load.assert_called_once()

    def test_init_load_error(self, mock_emb, temp_index_path):
        with patch("os.path.exists", return_value=True):
            with patch(
                "langchain_community.vectorstores.FAISS.load_local",
                side_effect=Exception("Load error"),
            ):
                repo = ChunkFAISSRepository(mock_emb, temp_index_path)
                assert repo._vector_store is None

    def test_create_documents_new_store(self, mock_emb, temp_index_path):
        with patch("os.path.exists", return_value=False):
            with patch(
                "langchain_community.vectorstores.FAISS.from_texts"
            ) as mock_from:
                mock_store = MagicMock()
                mock_from.return_value = mock_store
                repo = ChunkFAISSRepository(mock_emb, temp_index_path)

                # Test with extra metadata and content=None
                doc1 = self.create_mock_chunk(content="hello", extra={"key": "val"})
                doc2 = self.create_mock_chunk(content=None)
                ids = repo.create_documents([doc1, doc2])

                assert len(ids) == 1
                mock_from.assert_called_once()
                mock_store.save_local.assert_called_once()

    def test_create_documents_empty(self, mock_emb, temp_index_path):
        repo = ChunkFAISSRepository(mock_emb, temp_index_path)
        assert repo.create_documents([]) == []

    def test_create_documents_error(self, mock_emb, temp_index_path):
        with patch(
            "langchain_community.vectorstores.FAISS.from_texts",
            side_effect=Exception("Error"),
        ):
            repo = ChunkFAISSRepository(mock_emb, temp_index_path)
            with pytest.raises(Exception):
                repo.create_documents([self.create_mock_chunk()])

    def test_retriever_not_init(self, mock_emb, temp_index_path):
        repo = ChunkFAISSRepository(mock_emb, temp_index_path)
        assert repo.retriever("query") == []

    def test_retriever_semantic(self, mock_emb, temp_index_path):
        with patch("os.path.exists", return_value=True):
            with patch(
                "langchain_community.vectorstores.FAISS.load_local"
            ) as mock_load:
                mock_store = MagicMock()
                mock_load.return_value = mock_store
                repo = ChunkFAISSRepository(mock_emb, temp_index_path)

                mock_doc = MagicMock()
                mock_doc.page_content = "found"
                mock_doc.metadata = {
                    "id": str(uuid4()),
                    "job_id": str(uuid4()),
                    "content_source_id": str(uuid4()),
                    "source_type": "youtube",
                    "external_source": "vid",
                    "subject_id": str(uuid4()),
                    "embedding_model": "emb",
                }
                mock_store.similarity_search_with_score.return_value = [(mock_doc, 0.1)]

                results = repo.retriever("query", search_mode=SearchMode.SEMANTIC)
                assert len(results) == 1
                assert results[0].content == "found"

    def test_retriever_error(self, mock_emb, temp_index_path):
        with patch("os.path.exists", return_value=True):
            with patch(
                "langchain_community.vectorstores.FAISS.load_local"
            ) as mock_load:
                mock_store = MagicMock()
                mock_load.return_value = mock_store
                repo = ChunkFAISSRepository(mock_emb, temp_index_path)
                mock_store.similarity_search_with_score.side_effect = Exception(
                    "Search error"
                )
                with pytest.raises(Exception):
                    repo.retriever("query")

    def test_bm25_search_empty(self, mock_emb, temp_index_path, monkeypatch):
        monkeypatch.setitem(sys.modules, "rank_bm25", MagicMock())
        with patch("os.path.exists", return_value=True):
            with patch(
                "langchain_community.vectorstores.FAISS.load_local"
            ) as mock_load:
                mock_store = MagicMock()
                mock_load.return_value = mock_store
                repo = ChunkFAISSRepository(mock_emb, temp_index_path)
                mock_store.docstore._dict = {}
                assert repo._bm25_search("query", 5, None) == []

    def test_hybrid_search_empty(self, mock_emb, temp_index_path, monkeypatch):
        monkeypatch.setitem(sys.modules, "rank_bm25", MagicMock())
        with patch("os.path.exists", return_value=True):
            with patch(
                "langchain_community.vectorstores.FAISS.load_local"
            ) as mock_load:
                mock_store = MagicMock()
                mock_load.return_value = mock_store
                repo = ChunkFAISSRepository(mock_emb, temp_index_path)

                with patch.object(repo, "_semantic_search", return_value=[]):
                    with patch.object(repo, "_bm25_search", return_value=[]):
                        assert repo._hybrid_search("query", 5, None) == []

    def test_delete_not_init(self, mock_emb, temp_index_path):
        repo = ChunkFAISSRepository(mock_emb, temp_index_path)
        assert repo.delete({"id": "1"}) == 0

    def test_delete_no_filter(self, mock_emb, temp_index_path):
        with patch("os.path.exists", return_value=True):
            with patch("langchain_community.vectorstores.FAISS.load_local"):
                repo = ChunkFAISSRepository(mock_emb, temp_index_path)
                repo._vector_store = MagicMock()
                assert repo.delete(None) == 0

    def test_delete_error(self, mock_emb, temp_index_path):
        with patch("os.path.exists", return_value=True):
            with patch("langchain_community.vectorstores.FAISS.load_local"):
                repo = ChunkFAISSRepository(mock_emb, temp_index_path)
                repo._vector_store = MagicMock()
                repo._vector_store.delete.side_effect = Exception("Delete error")
                with pytest.raises(Exception):
                    repo.delete({"id": "1"})

    def test_list_chunks_not_init(self, mock_emb, temp_index_path):
        repo = ChunkFAISSRepository(mock_emb, temp_index_path)
        assert repo.list_chunks(None) == []

    def test_list_chunks_error(self, mock_emb, temp_index_path):
        with patch("os.path.exists", return_value=True):
            with patch("langchain_community.vectorstores.FAISS.load_local"):
                repo = ChunkFAISSRepository(mock_emb, temp_index_path)
                repo._vector_store = MagicMock()
                # docstore attribute missing to trigger error
                del repo._vector_store.docstore
                with pytest.raises(Exception):
                    repo.list_chunks(None)

    def test_is_ready(self, mock_emb, temp_index_path):
        repo = ChunkFAISSRepository(mock_emb, temp_index_path)
        assert repo.is_ready() is False
        repo._vector_store = MagicMock()
        assert repo.is_ready() is True
