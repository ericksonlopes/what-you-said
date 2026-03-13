from typing import List, Optional, Any
from typing import cast

from src.config.logger import Logger
from src.infrastructure.repositories.sql.connector import Connector
from src.infrastructure.repositories.sql.models.chunk_index import ChunkIndexModel
from src.infrastructure.repositories.sql.models.content_source import ContentSourceModel
from uuid import UUID
logger = Logger()


class ChunkIndexSQLRepository:
    """Repository for the chunk_index table providing CRUD and simple search helpers."""

    def create_chunks(self, chunks: List[dict]) -> List[UUID]:
        """Insert multiple chunk index rows. Each chunk should be a dict with keys matching ChunkIndexModel."""
        with Connector() as session:
            try:
                orm_objs = []
                for ch in chunks:
                    obj = ChunkIndexModel(
                        id=ch.get("id"),
                        content_source_id=ch.get("content_source_id"),
                        job_id=ch.get("job_id"),
                        chunk_id=ch.get("chunk_id"),
                        chars=ch.get("chars", 0),
                        language=ch.get("language"),
                        version_number=ch.get("version_number", 1),
                    )
                    session.add(obj)
                    orm_objs.append(obj)

                session.commit()

                return [cast(UUID, o.id) for o in orm_objs]
            except Exception as e:
                session.rollback()
                logger.error("Error creating chunk index rows", context={"error": str(e)})
                raise

    def list_by_content_source(self, content_source_id: UUID, limit: int = 1000) -> List[ChunkIndexModel]:
        with Connector() as session:
            return session.query(ChunkIndexModel).filter_by(content_source_id=content_source_id).limit(limit).all()

    def delete_by_content_source(self, content_source_id: UUID) -> int:
        with Connector() as session:
            try:
                deleted = session.query(ChunkIndexModel).filter_by(content_source_id=content_source_id).delete(synchronize_session=False)
                session.commit()
                return int(deleted)
            except Exception as e:
                session.rollback()
                logger.error("Error deleting chunk index rows", context={"error": str(e)})
                raise

    def search(self, query: Optional[str], top_k: int = 10, filters: Optional[Any] = None) -> List[ChunkIndexModel]:
        with Connector() as session:
            q = session.query(ChunkIndexModel).outerjoin(ContentSourceModel, ChunkIndexModel.content_source_id == ContentSourceModel.id)
            if isinstance(filters, dict):
                q = q.filter_by(**filters)
            if query:
                pattern = f"%{query}%"
                q = q.filter(
                    (ContentSourceModel.title.ilike(pattern)) | (ContentSourceModel.external_source.ilike(pattern)) | (ChunkIndexModel.chunk_id.ilike(pattern))
                )
            return q.limit(top_k).all()
