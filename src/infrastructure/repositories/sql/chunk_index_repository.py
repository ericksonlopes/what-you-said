from typing import List, Optional, Any
from typing import cast
from uuid import UUID

from src.config.logger import Logger
from src.infrastructure.repositories.sql.connector import Connector
from src.infrastructure.repositories.sql.models.chunk_index import ChunkIndexModel
from src.infrastructure.repositories.sql.models.content_source import ContentSourceModel

from sqlalchemy.orm import joinedload

logger = Logger()


class ChunkIndexSQLRepository:
    """Repository for the chunk_index table providing CRUD and simple search helpers."""

    def create_chunks(self, chunks: List[dict]) -> List[UUID]:
        """Insert multiple chunk index rows. Each chunk should be a dict with keys matching ChunkIndexModel."""
        with Connector() as session:
            try:
                orm_objs = []
                for ch in chunks:
                    content_val = ch.get("content")
                    content_size = len(content_val) if content_val else 0

                    obj = ChunkIndexModel(
                        id=ch.get("id"),
                        content_source_id=ch.get("content_source_id"),
                        job_id=ch.get("job_id"),
                        chunk_id=ch.get("chunk_id"),
                        content=content_val,
                        chars=ch.get("chars", content_size),
                        tokens_count=ch.get("tokens_count"),
                        language=ch.get("language"),
                        version_number=ch.get("version_number", 1),
                        vector_store_type=ch.get("vector_store_type"),
                    )
                    session.add(obj)
                    orm_objs.append(obj)

                session.commit()
                logger.debug(
                    "Created chunk index rows", context={"count": len(orm_objs)}
                )

                return [cast(UUID, o.id) for o in orm_objs]
            except Exception as e:
                session.rollback()
                logger.error(
                    "Error creating chunk index rows", context={"error": str(e)}
                )
                raise

    def list_by_content_source(
        self,
        content_source_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[ChunkIndexModel]:
        with Connector() as session:
            query = (
                session.query(ChunkIndexModel)
                .options(joinedload(ChunkIndexModel.content_source))
                .filter_by(content_source_id=content_source_id)
                .order_by(ChunkIndexModel.created_at.asc())
            )
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)
            return query.all()

    def list_chunks(
        self,
        limit: int = 100,
        offset: int = 0,
        source_id: Optional[UUID] = None,
        search_query: Optional[str] = None,
    ) -> List[ChunkIndexModel]:
        with Connector() as session:
            query = (
                session.query(ChunkIndexModel)
                .options(joinedload(ChunkIndexModel.content_source))
                .order_by(ChunkIndexModel.created_at.desc())
            )
            if source_id:
                query = query.filter_by(content_source_id=source_id)
            if search_query:
                query = query.filter(ChunkIndexModel.content.ilike(f"%{search_query}%"))
            return query.limit(limit).offset(offset).all()

    def count_by_content_source(self, content_source_id: UUID) -> int:
        with Connector() as session:
            return (
                session.query(ChunkIndexModel)
                .filter_by(content_source_id=content_source_id)
                .count()
            )

    def delete_by_content_source(self, content_source_id: UUID) -> int:
        with Connector() as session:
            try:
                deleted = (
                    session.query(ChunkIndexModel)
                    .filter_by(content_source_id=content_source_id)
                    .delete(synchronize_session=False)
                )
                session.commit()
                return int(deleted)
            except Exception as e:
                session.rollback()
                logger.error(
                    "Error deleting chunk index rows", context={"error": str(e)}
                )
                raise

    def search(
        self, query: Optional[str], top_k: int = 10, filters: Optional[Any] = None
    ) -> List[ChunkIndexModel]:
        with Connector() as session:
            q = (
                session.query(ChunkIndexModel)
                .options(joinedload(ChunkIndexModel.content_source))
                .outerjoin(
                    ContentSourceModel,
                    ChunkIndexModel.content_source_id == ContentSourceModel.id,
                )
            )
            if isinstance(filters, dict):
                q = q.filter_by(**filters)
            if query:
                pattern = f"%{query}%"
                q = q.filter(
                    (ContentSourceModel.title.ilike(pattern))
                    | (ContentSourceModel.external_source.ilike(pattern))
                    | (ChunkIndexModel.chunk_id.ilike(pattern))
                )
            return q.limit(top_k).all()

    def delete_chunk(self, chunk_id: UUID) -> bool:
        with Connector() as session:
            try:
                result = session.query(ChunkIndexModel).filter_by(id=chunk_id).delete()
                session.commit()
                return result > 0
            except Exception as e:
                session.rollback()
                logger.error(
                    "Error deleting individual chunk",
                    context={"chunk_id": str(chunk_id), "error": str(e)},
                )
                raise

    def update_chunk(self, chunk_id: UUID, content: str) -> bool:
        with Connector() as session:
            try:
                chunk = session.query(ChunkIndexModel).filter_by(id=chunk_id).first()
                if chunk:
                    chunk.content = content
                    chunk.chars = len(content)
                    session.commit()
                    return True
                return False
            except Exception as e:
                session.rollback()
                logger.error(
                    "Error updating individual chunk",
                    context={"chunk_id": str(chunk_id), "error": str(e)},
                )
                raise

    def get_by_id(self, chunk_id: UUID) -> Optional[ChunkIndexModel]:
        with Connector() as session:
            try:
                return (
                    session.query(ChunkIndexModel)
                    .options(joinedload(ChunkIndexModel.content_source))
                    .filter_by(id=chunk_id)
                    .first()
                )
            except Exception as e:
                logger.error(
                    "Error fetching individual chunk",
                    context={"chunk_id": str(chunk_id), "error": str(e)},
                )
                return None
