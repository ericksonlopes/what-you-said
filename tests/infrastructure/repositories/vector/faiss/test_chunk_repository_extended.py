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

# Mock rank_bm25 for hybrid tests
mock_bm25_lib = MagicMock()
sys.modules["rank_bm25"] = mock_bm25_lib

from src.infrastructure.repositories.vector.faiss.chunk_repository import (  # noqa: E402
    ChunkFAISSRepository,
)
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel  # noqa: E402
from src.domain.entities.enums.search_mode_enum import SearchMode  # noqa: E402


@pytest.mark.ChunkFAISSRepository
class TestChunkFAISSRepositoryExtended:
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

    def test_init_load_error(self, mock_emb, temp_index_path):
        with patch("os.path.exists", return_value=True):
            with patch(
                "langchain_community.vectorstores.FAISS.load_local",
                side_effect=Exception("Load fail"),
            ):
                repo = ChunkFAISSRepository(mock_emb, temp_index_path)
                assert repo._vector_store is None

    def test_create_documents_empty_list(self, mock_emb, temp_index_path):
        repo = ChunkFAISSRepository(mock_emb, temp_index_path)
        assert repo.create_documents([]) == []

    def test_create_documents_all_none_content(self, mock_emb, temp_index_path):
        repo = ChunkFAISSRepository(mock_emb, temp_index_path)
        doc = ChunkModel(
            id=uuid4(),
            content=None,  # type: ignore
            job_id=uuid4(),
            content_source_id=uuid4(),
            source_type="youtube",
            external_source="vid",
            subject_id=uuid4(),
            embedding_model="emb",
        )
        assert repo.create_documents([doc]) == []

    def test_bm25_import_error(self, mock_emb, temp_index_path):
        with patch("os.path.exists", return_value=True):
            with patch("langchain_community.vectorstores.FAISS.load_local"):
                repo = ChunkFAISSRepository(mock_emb, temp_index_path)

                # Mock ONLY the specific import of BM25Okapi
                orig_import = __import__

                def mocked_import(name, *args, **kwargs):
                    if name == "rank_bm25":
                        raise ImportError("Custom Error")
                    return orig_import(name, *args, **kwargs)

                with patch("builtins.__import__", side_effect=mocked_import):
                    with pytest.raises(ImportError):
                        repo._bm25_search("query", 5, None)

    def test_hybrid_search_success(self, mock_emb, temp_index_path, monkeypatch):
        mock_bm25 = MagicMock()
        monkeypatch.setattr("rank_bm25.BM25Okapi", MagicMock(return_value=mock_bm25))

        with patch("os.path.exists", return_value=True):
            with patch(
                "langchain_community.vectorstores.FAISS.load_local"
            ) as mock_load:
                mock_store = MagicMock()
                mock_load.return_value = mock_store
                repo = ChunkFAISSRepository(mock_emb, temp_index_path)

                cid = str(uuid4())
                mock_doc = MagicMock()
                mock_doc.page_content = "content"
                mock_doc.metadata = {
                    "id": cid,
                    "job_id": str(uuid4()),
                    "content_source_id": str(uuid4()),
                    "source_type": "youtube",
                    "external_source": "vid",
                    "subject_id": str(uuid4()),
                    "embedding_model": "emb",
                }

                # Semantic results
                mock_store.similarity_search_with_score.return_value = [(mock_doc, 0.1)]
                # BM25 results
                mock_store.docstore._dict = {cid: mock_doc}
                mock_bm25.get_scores.return_value = [1.0]

                results = repo.retriever("query", search_mode=SearchMode.HYBRID)
                assert len(results) >= 1
                assert results[0].content == "content"

    def test_delete_simple_id(self, mock_emb, temp_index_path):
        with patch("os.path.exists", return_value=True):
            with patch(
                "langchain_community.vectorstores.FAISS.load_local"
            ) as mock_load:
                mock_store = MagicMock()
                mock_load.return_value = mock_store
                repo = ChunkFAISSRepository(mock_emb, temp_index_path)

                cid = uuid4()
                repo.delete({"id": cid})
                mock_store.delete.assert_called_with([str(cid)])

    def test_list_chunks_with_limit(self, mock_emb, temp_index_path):
        with patch("os.path.exists", return_value=True):
            with patch(
                "langchain_community.vectorstores.FAISS.load_local"
            ) as mock_load:
                mock_store = MagicMock()
                mock_load.return_value = mock_store
                repo = ChunkFAISSRepository(mock_emb, temp_index_path)

                d1 = MagicMock()
                d1.page_content = "text a"
                d1.metadata = {
                    "id": str(uuid4()),
                    "job_id": str(uuid4()),
                    "content_source_id": str(uuid4()),
                    "source_type": "youtube",
                    "external_source": "vid",
                    "subject_id": str(uuid4()),
                    "embedding_model": "emb",
                }
                mock_store.docstore._dict = {"1": d1}

                res = repo.list_chunks(None, limit=1)
                assert len(res) == 1
                assert res[0].content == "text a"

    def test_save_no_store(self, mock_emb, temp_index_path):
        repo = ChunkFAISSRepository(mock_emb, temp_index_path)
        repo._save()  # Should not raise
