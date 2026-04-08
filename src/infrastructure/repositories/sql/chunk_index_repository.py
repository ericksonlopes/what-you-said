from typing import Any, List, Optional, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import joinedload

from src.config.logger import Logger
from src.infrastructure.connectors.connector_sql import Connector
from src.infrastructure.repositories.sql.models.chunk_index import ChunkIndexModel
from src.infrastructure.repositories.sql.models.content_source import ContentSourceModel
from src.infrastructure.repositories.sql.utils.utils import ensure_uuid

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
                        index=ch.get("index"),
                        content=content_val,
                        chars=ch.get("chars", content_size),
                        tokens_count=ch.get("tokens_count"),
                        language=ch.get("language"),
                        source_type=ch.get("source_type"),
                        subject_id=ch.get("subject_id"),
                        external_source=ch.get("external_source"),
                        extra=ch.get("extra"),
                        version_number=ch.get("version_number", 1),
                        vector_store_type=ch.get("vector_store_type"),
                    )
                    session.add(obj)
                    orm_objs.append(obj)

                session.commit()

                # Update ContentSource count (increment by the number of chunks added)
                if orm_objs:
                    # Collect content_source_ids to update
                    source_ids = {o.content_source_id for o in orm_objs if o.content_source_id}
                    for sid in source_ids:
                        count = sum(1 for o in orm_objs if o.content_source_id == sid)
                        session.query(ContentSourceModel).filter_by(id=sid).update(
                            {"chunks": ContentSourceModel.chunks + count}
                        )
                    session.commit()

                logger.debug("Created chunk index rows", context={"count": len(orm_objs)})

                return [cast(UUID, o.id) for o in orm_objs]
            except Exception as e:
                session.rollback()
                logger.error("Error creating chunk index rows", context={"error": str(e)})
                raise

    def list_by_content_source(
        self,
        content_source_id: Any,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[ChunkIndexModel]:
        content_source_id = ensure_uuid(content_source_id)
        with Connector() as session:
            query = (
                session.query(ChunkIndexModel)
                .options(joinedload(ChunkIndexModel.content_source))
                .filter_by(content_source_id=content_source_id)
                .order_by(ChunkIndexModel.index.asc(), ChunkIndexModel.created_at.asc())
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
        source_id: Optional[Any] = None,
        search_query: Optional[str] = None,
    ) -> List[ChunkIndexModel]:
        source_id = ensure_uuid(source_id)
        with Connector() as session:
            query = session.query(ChunkIndexModel).options(joinedload(ChunkIndexModel.content_source))

            if source_id:
                query = query.filter_by(content_source_id=source_id).order_by(
                    ChunkIndexModel.index.asc(), ChunkIndexModel.created_at.asc()
                )
            else:
                query = query.order_by(ChunkIndexModel.created_at.desc())

            if search_query:
                query = query.filter(ChunkIndexModel.content.ilike(f"%{search_query}%"))

            return query.limit(limit).offset(offset).all()

    def count_by_content_source(self, content_source_id: Any) -> int:
        content_source_id = ensure_uuid(content_source_id)
        with Connector() as session:
            return session.query(ChunkIndexModel).filter_by(content_source_id=content_source_id).count()

    def delete_by_content_source(self, content_source_id: Any) -> int:
        content_source_id = ensure_uuid(content_source_id)
        with Connector() as session:
            try:
                deleted = (
                    session.query(ChunkIndexModel)
                    .filter_by(content_source_id=content_source_id)
                    .delete(synchronize_session=False)
                )

                # Update ContentSource count to 0
                session.query(ContentSourceModel).filter_by(id=content_source_id).update({"chunks": 0})

                session.commit()
                return int(deleted)
            except Exception as e:
                session.rollback()
                logger.error("Error deleting chunk index rows", context={"error": str(e)})
                raise

    def delete_by_job_id(self, job_id: Any) -> int:
        job_id = ensure_uuid(job_id)
        """Delete all chunks associated with a specific ingestion job."""
        with Connector() as session:
            try:
                # 1. Find the content_source_id before deleting
                chunks = session.query(ChunkIndexModel.content_source_id).filter_by(job_id=job_id).all()
                if not chunks:
                    return 0

                source_ids = {c.content_source_id for c in chunks if c.content_source_id}

                # 2. Delete the chunks
                deleted = session.query(ChunkIndexModel).filter_by(job_id=job_id).delete(synchronize_session=False)

                # 3. Update ContentSource counts (decrement by the number of chunks deleted)
                if deleted > 0:
                    for sid in source_ids:
                        count = sum(1 for c in chunks if c.content_source_id == sid)
                        session.query(ContentSourceModel).filter_by(id=sid).update(
                            {"chunks": sa.text(f"chunks - {count}")}
                        )

                session.commit()
                logger.info(
                    "Deleted chunks by job_id",
                    context={"job_id": str(job_id), "count": deleted},
                )
                return int(deleted)
            except Exception as e:
                session.rollback()
                logger.error(
                    "Error deleting chunks by job_id",
                    context={"job_id": str(job_id), "error": str(e)},
                )
                raise

    def search(self, query: Optional[str], top_k: int = 10, filters: Optional[Any] = None) -> List[ChunkIndexModel]:
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
                for key, value in filters.items():
                    if hasattr(ChunkIndexModel, key):
                        q = q.filter(getattr(ChunkIndexModel, key) == value)
                    elif hasattr(ContentSourceModel, key):
                        q = q.filter(getattr(ContentSourceModel, key) == value)
            if query:
                pattern = f"%{query}%"
                q = q.filter(
                    (ContentSourceModel.title.ilike(pattern))
                    | (ContentSourceModel.external_source.ilike(pattern))
                    | (ChunkIndexModel.chunk_id.ilike(pattern))
                )
            return q.limit(top_k).all()

    def delete_chunk(self, chunk_id: Any) -> bool:
        chunk_id = ensure_uuid(chunk_id)
        with Connector() as session:
            try:
                # 1. Get content_source_id before deleting
                chunk = session.query(ChunkIndexModel).filter_by(id=chunk_id).first()
                if not chunk:
                    return False

                content_source_id = chunk.content_source_id

                # 2. Delete the chunk
                session.delete(chunk)

                # 3. Decrement count in ContentSource
                session.query(ContentSourceModel).filter_by(id=content_source_id).update(
                    {"chunks": ContentSourceModel.chunks - 1}
                )

                session.commit()
                return True
            except Exception as e:
                session.rollback()
                logger.error(
                    "Error deleting individual chunk",
                    context={"chunk_id": str(chunk_id), "error": str(e)},
                )
                raise

    def update_chunk(self, chunk_id: Any, content: str) -> bool:
        chunk_id = ensure_uuid(chunk_id)
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

    def get_by_id(self, chunk_id: Any) -> Optional[ChunkIndexModel]:
        chunk_id = ensure_uuid(chunk_id)
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

    def update_is_active(self, chunk_id: Any, is_active: bool) -> bool:
        """Update the is_active flag of a chunk."""
        chunk_id = ensure_uuid(chunk_id)
        with Connector() as session:
            try:
                chunk = session.query(ChunkIndexModel).filter_by(id=chunk_id).first()
                if chunk:
                    chunk.is_active = is_active
                    session.commit()
                    return True
                return False
            except Exception as e:
                session.rollback()
                logger.error(
                    "Error updating chunk is_active",
                    context={"chunk_id": str(chunk_id), "error": str(e)},
                )
                raise
