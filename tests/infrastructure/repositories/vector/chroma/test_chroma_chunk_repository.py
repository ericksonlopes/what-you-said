import sys
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

# Mock dependencies at module level
mock_chromadb = MagicMock()
mock_langchain_chroma = MagicMock()
sys.modules["chromadb"] = mock_chromadb
sys.modules["langchain_chroma"] = mock_langchain_chroma

from src.infrastructure.repositories.vector.chroma.chunk_repository import (  # noqa: E402
    ChunkChromaRepository,
)
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel  # noqa: E402
from src.domain.entities.enums.search_mode_enum import SearchMode  # noqa: E402


@pytest.mark.ChunkChromaRepository
class TestChunkChromaRepository:
    @pytest.fixture
    def mock_emb(self):
        return MagicMock()

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
        )

    def test_init_success(self, mock_emb):
        with patch("chromadb.HttpClient") as mock_http:
            with patch("langchain_chroma.Chroma"):
                repo = ChunkChromaRepository(mock_emb)
                assert repo._chroma_client is not None
                assert repo._vector_store is not None
                mock_http.assert_called_once()

    def test_init_failure(self, mock_emb):
        with patch("chromadb.HttpClient", side_effect=Exception("Connection failed")):
            repo = ChunkChromaRepository(mock_emb)
            assert repo._chroma_client is None
            assert repo._vector_store is None

    def test_create_documents_success(self, mock_emb):
        with patch("chromadb.HttpClient"):
            with patch("langchain_chroma.Chroma") as mock_chroma_class:
                mock_store = MagicMock()
                mock_chroma_class.return_value = mock_store
                repo = ChunkChromaRepository(mock_emb)

                doc = self.create_mock_chunk(content="test text")
                res = repo.create_documents([doc])
                assert len(res) == 1
                mock_store.add_texts.assert_called_once()

    def test_create_documents_not_init(self, mock_emb):
        with patch("chromadb.HttpClient", side_effect=Exception()):
            repo = ChunkChromaRepository(mock_emb)
            with pytest.raises(ConnectionError, match="ChromaDB is not initialized"):
                repo.create_documents([MagicMock()])

    def test_retriever_semantic(self, mock_emb):
        with patch("chromadb.HttpClient"):
            with patch("langchain_chroma.Chroma") as mock_chroma_class:
                mock_store = MagicMock()
                mock_chroma_class.return_value = mock_store
                repo = ChunkChromaRepository(mock_emb)

                # Mock similarity search
                mock_doc = MagicMock()
                mock_doc.page_content = "content"
                mock_doc.metadata = {
                    "id": str(uuid4()),
                    "job_id": str(uuid4()),
                    "content_source_id": str(uuid4()),
                    "source_type": "youtube",
                    "external_source": "vid",
                    "subject_id": str(uuid4()),
                    "embedding_model": "emb",
                }
                mock_store.similarity_search_with_score.return_value = [(mock_doc, 0.5)]

                results = repo.retriever("query", search_mode=SearchMode.SEMANTIC)
                assert len(results) == 1
                assert results[0].content == "content"

    def test_bm25_search(self, mock_emb, monkeypatch):
        mock_bm25 = MagicMock()
        mock_bm25_class = MagicMock(return_value=mock_bm25)
        monkeypatch.setitem(sys.modules, "rank_bm25", MagicMock())
        monkeypatch.setattr("rank_bm25.BM25Okapi", mock_bm25_class, raising=False)

        mock_np = MagicMock()
        monkeypatch.setitem(sys.modules, "numpy", mock_np)
        mock_np.argsort.return_value = [0]

        with patch("chromadb.HttpClient") as mock_http:
            mock_client = MagicMock()
            mock_http.return_value = mock_client
            with patch("langchain_chroma.Chroma"):
                repo = ChunkChromaRepository(mock_emb)

                mock_col = MagicMock()
                mock_client.get_collection.return_value = mock_col
                mock_col.get.return_value = {
                    "ids": ["1"],
                    "documents": ["text"],
                    "metadatas": [
                        {
                            "id": str(uuid4()),
                            "job_id": str(uuid4()),
                            "content_source_id": str(uuid4()),
                            "source_type": "youtube",
                            "external_source": "vid",
                            "subject_id": str(uuid4()),
                            "embedding_model": "emb",
                        }
                    ],
                }

                mock_bm25.get_scores.return_value = [10.0]

                results = repo.retriever("query", search_mode=SearchMode.BM25)
                assert len(results) == 1
                assert results[0].content == "text"

    def test_hybrid_search(self, mock_emb, monkeypatch):
        # Mock dependencies for BM25
        mock_bm25 = MagicMock()
        monkeypatch.setitem(sys.modules, "rank_bm25", MagicMock())
        monkeypatch.setattr(
            "rank_bm25.BM25Okapi", MagicMock(return_value=mock_bm25), raising=False
        )
        mock_np = MagicMock()
        monkeypatch.setitem(sys.modules, "numpy", mock_np)
        mock_np.argsort.return_value = [0]

        with patch("chromadb.HttpClient") as mock_http:
            mock_client = MagicMock()
            mock_http.return_value = mock_client
            with patch("langchain_chroma.Chroma") as mock_chroma_class:
                mock_store = MagicMock()
                mock_chroma_class.return_value = mock_store
                repo = ChunkChromaRepository(mock_emb)

                cid = str(uuid4())
                mock_doc = MagicMock()
                mock_doc.page_content = "hybrid text"
                mock_doc.metadata = {
                    "id": cid,
                    "job_id": str(uuid4()),
                    "content_source_id": str(uuid4()),
                    "source_type": "youtube",
                    "external_source": "vid",
                    "subject_id": str(uuid4()),
                    "embedding_model": "emb",
                }

                # Mock Semantic
                mock_store.similarity_search_with_score.return_value = [(mock_doc, 0.1)]

                # Mock BM25
                mock_col = MagicMock()
                mock_client.get_collection.return_value = mock_col
                mock_col.get.return_value = {
                    "ids": [cid],
                    "documents": ["hybrid text"],
                    "metadatas": [mock_doc.metadata],
                }
                mock_bm25.get_scores.return_value = [1.0]

                results = repo.retriever("query", search_mode=SearchMode.HYBRID)
                assert len(results) == 1
                assert results[0].content == "hybrid text"

    def test_list_chunks(self, mock_emb):
        with patch("chromadb.HttpClient") as mock_http:
            mock_client = MagicMock()
            mock_http.return_value = mock_client
            with patch("langchain_chroma.Chroma"):
                repo = ChunkChromaRepository(mock_emb)
                mock_col = MagicMock()
                mock_client.get_collection.return_value = mock_col
                mock_col.get.return_value = {
                    "ids": ["id1"],
                    "documents": ["doc1"],
                    "metadatas": [
                        {
                            "id": str(uuid4()),
                            "job_id": str(uuid4()),
                            "content_source_id": str(uuid4()),
                            "source_type": "youtube",
                            "external_source": "vid",
                            "subject_id": str(uuid4()),
                            "embedding_model": "emb",
                        }
                    ],
                }

                res = repo.list_chunks(filters={"a": "b"})
                assert len(res) == 1
                assert res[0].content == "doc1"

    def test_delete_with_filters(self, mock_emb):
        with patch("chromadb.HttpClient") as mock_http:
            mock_client = MagicMock()
            mock_http.return_value = mock_client
            with patch("langchain_chroma.Chroma"):
                repo = ChunkChromaRepository(mock_emb)
                mock_col = MagicMock()
                mock_client.get_collection.return_value = mock_col
                mock_col.get.return_value = {"ids": ["id1"]}

                # Multiple filters triggers $and
                deleted = repo.delete(filters={"source": "val", "type": "pdf"})
                assert deleted == 1
                mock_col.delete.assert_called_once_with(ids=["id1"])

    def test_delete_no_filters(self, mock_emb):
        with patch("chromadb.HttpClient"):
            with patch("langchain_chroma.Chroma"):
                repo = ChunkChromaRepository(mock_emb)
                assert repo.delete(filters=None) == 0
                assert repo.delete(filters={}) == 0

    def test_is_ready(self, mock_emb):
        with patch("chromadb.HttpClient") as mock_http:
            mock_client = MagicMock()
            mock_http.return_value = mock_client
            with patch("langchain_chroma.Chroma"):
                repo = ChunkChromaRepository(mock_emb)

                mock_client.heartbeat.return_value = True
                assert repo.is_ready() is True

                mock_client.heartbeat.side_effect = Exception()
                assert repo.is_ready() is False
