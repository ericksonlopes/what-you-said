from typing import Optional, cast
from uuid import UUID

from src.config.logger import Logger
from src.infrastructure.repositories.sql.connector import Connector
from src.infrastructure.repositories.sql.models.query_log import QueryLogModel

logger = Logger()


class QueryLogSQLRepository:
    """Repository helpers for query_logs table."""

    @staticmethod
    def create_log(subject_id: Optional[UUID], query_text: str,
                   top_k: Optional[int] = None, latency_ms: Optional[int] = None) -> UUID:
        with Connector() as session:
            try:
                q = QueryLogModel(
                    subject_id=subject_id,
                    query_text=query_text,
                    top_k=top_k,
                    latency_ms=latency_ms,
                )
                session.add(q)
                session.commit()
                session.refresh(q)
                return cast(UUID, q.id)
            except Exception as e:
                logger.error("Failed to create query log",
                             context={"error": str(e), "subject_id": str(subject_id), "query_text": query_text})
                session.rollback()
                raise
