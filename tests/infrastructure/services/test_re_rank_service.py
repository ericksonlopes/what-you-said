import pytest
import sys
from unittest.mock import MagicMock, patch
from uuid import uuid4

# Mock flashrank at module level since it might not be installed in all environments
mock_flashrank = MagicMock()
sys.modules["flashrank"] = mock_flashrank

from src.infrastructure.services.re_rank_service import ReRankService  # noqa: E402
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel  # noqa: E402


@pytest.mark.ReRankService
class TestReRankService:
    def test_init_success(self, monkeypatch):
        mock_ranker_class = MagicMock()
        monkeypatch.setattr(
            "src.infrastructure.services.re_rank_service.Ranker", mock_ranker_class
        )

        service = ReRankService(model_name="test-model")

        assert service._ranker is not None
        mock_ranker_class.assert_called_once_with(
            model_name="test-model", cache_dir="/tmp/flashrank_cache"
        )

    def test_init_failure(self, monkeypatch):
        mock_ranker_class = MagicMock(side_effect=Exception("Failed to load"))
        monkeypatch.setattr(
            "src.infrastructure.services.re_rank_service.Ranker", mock_ranker_class
        )

        service = ReRankService()

        assert service._ranker is None

    def test_rerank_no_ranker(self):
        # Create service with failed init
        with patch(
            "src.infrastructure.services.re_rank_service.Ranker",
            side_effect=Exception(),
        ):
            service = ReRankService()

        doc = ChunkModel(
            id=uuid4(),
            content="test",
            job_id=uuid4(),
            content_source_id=uuid4(),
            source_type="youtube",
            external_source="vid1",
            subject_id=uuid4(),
            embedding_model="test-emb",
        )
        docs = [doc]
        result = service.rerank("query", docs)

        assert result == docs

    def test_rerank_empty_docs(self, monkeypatch):
        mock_ranker = MagicMock()
        monkeypatch.setattr(
            "src.infrastructure.services.re_rank_service.Ranker",
            MagicMock(return_value=mock_ranker),
        )
        service = ReRankService()

        result = service.rerank("query", [])

        assert result == []

    def test_rerank_success(self, monkeypatch):
        mock_ranker = MagicMock()
        monkeypatch.setattr(
            "src.infrastructure.services.re_rank_service.Ranker",
            MagicMock(return_value=mock_ranker),
        )
        service = ReRankService()

        common_args = {
            "job_id": uuid4(),
            "content_source_id": uuid4(),
            "source_type": "youtube",
            "external_source": "vid1",
            "subject_id": uuid4(),
            "embedding_model": "test-emb",
        }

        doc1 = ChunkModel(id=uuid4(), content="text 1", **common_args)
        doc2 = ChunkModel(id=uuid4(), content="text 2", **common_args)
        docs = [doc1, doc2]

        # Mock flashrank response
        mock_ranker.rerank.return_value = [
            {"meta": {"model": doc2}, "score": 0.9},
            {"meta": {"model": doc1}, "score": 0.1},
        ]

        result = service.rerank("best text", docs)

        assert len(result) == 2
        assert result[0] == doc2
        assert result[0].score == 0.9
        assert result[1] == doc1
        assert result[1].score == 0.1

    def test_rerank_exception(self, monkeypatch):
        mock_ranker = MagicMock()
        mock_ranker.rerank.side_effect = Exception("Runtime error")
        monkeypatch.setattr(
            "src.infrastructure.services.re_rank_service.Ranker",
            MagicMock(return_value=mock_ranker),
        )
        service = ReRankService()

        doc = ChunkModel(
            id=uuid4(),
            content="test",
            job_id=uuid4(),
            content_source_id=uuid4(),
            source_type="youtube",
            external_source="vid1",
            subject_id=uuid4(),
            embedding_model="test-emb",
        )
        docs = [doc]
        result = service.rerank("query", docs)

        # Should return original docs on error
        assert result == docs
