from typing import List
from flashrank import Ranker, RerankRequest
from src.config.logger import Logger
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel

logger = Logger()


class ReRankService:
    """Service for re-ranking search results using FlashRank (Cross-Encoders)."""

    def __init__(self, model_name: str = "ms-marco-MiniLM-L-12-v2"):
        try:
            logger.info("Initializing FlashRank", context={"model_name": model_name})
            self._ranker = Ranker(
                model_name=model_name, cache_dir="/tmp/flashrank_cache"
            )
        except Exception as e:
            logger.error(e, context={"action": "initialize_flashrank"})
            self._ranker = None

    def rerank(self, query: str, documents: List[ChunkModel]) -> List[ChunkModel]:
        """Re-rank a list of ChunkModels based on the query."""
        if not self._ranker or not documents:
            return documents

        try:
            logger.debug(
                "Re-ranking documents",
                context={"query": query, "count": len(documents)},
            )

            # FlashRank expects a list of dicts with 'id' and 'text'
            passages = [
                {"id": str(doc.id), "text": doc.content, "meta": {"model": doc}}
                for doc in documents
            ]

            rerank_request = RerankRequest(query=query, passages=passages)
            results = self._ranker.rerank(rerank_request)

            # Reconstruct ChunkModels from re-ranked results
            reranked_docs = []
            for res in results:
                doc = res["meta"]["model"]
                # Update score with the re-ranked score (0-1)
                doc.score = float(res["score"])
                reranked_docs.append(doc)

            return reranked_docs
        except Exception as e:
            logger.error(e, context={"action": "rerank", "query": query})
            return documents
