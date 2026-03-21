from datetime import datetime, timezone
from typing import Optional, List
from typing import cast
from uuid import UUID

from src.config.logger import Logger
from src.infrastructure.repositories.sql.connector import Connector
from src.infrastructure.repositories.sql.models.content_source import ContentSourceModel

logger = Logger()


class ContentSourceSQLRepository:
    """Repository for content_sources table (basic CRUD helpers)."""

    def create(
        self,
        subject_id: Optional[UUID],
        source_type: str,
        external_source: str,
        title: Optional[str] = None,
        language: Optional[str] = None,
        embedding_model: Optional[str] = None,
        dimensions: Optional[int] = None,
        status: Optional[str] = None,
        processing_status: Optional[str] = None,
        chunks: Optional[int] = None,
        chars: Optional[int] = None,
        total_tokens: Optional[int] = None,
        max_tokens_per_chunk: Optional[int] = None,
        source_metadata: Optional[dict] = None,
    ) -> UUID:
        with Connector() as session:
            extra = {}
            try:
                extra = {
                    "subject_id": subject_id,
                    "source_type": source_type,
                    "external_source": external_source,
                    "title": title,
                    "language": language,
                    "embedding_model": embedding_model,
                    "dimensions": dimensions,
                    "status": status,
                    "processing_status": processing_status,
                    "chunks": chunks,
                    "chars": chars,
                    "total_tokens": total_tokens,
                    "max_tokens_per_chunk": max_tokens_per_chunk,
                    "source_metadata": source_metadata,
                }
                logger.debug("Creating ContentSource", context=extra)
                cs = ContentSourceModel(
                    subject_id=subject_id,
                    source_type=source_type,
                    external_source=external_source,
                    title=title,
                    language=language,
                    embedding_model=embedding_model,
                    dimensions=dimensions,
                    status=status or "active",
                    processing_status=processing_status or "pending",
                    chunks=chunks or 0,
                    total_tokens=total_tokens,
                    max_tokens_per_chunk=max_tokens_per_chunk,
                    source_metadata=source_metadata,
                )
                session.add(cs)
                session.commit()
                session.refresh(cs)
                logger.debug(
                    "ContentSource created successfully",
                    context={"id": cs.id, "processing_status": cs.processing_status},
                )

                return cast(UUID, cs.id)
            except Exception as e:
                logger.error(
                    "Error creating ContentSource", context={**extra, "error": str(e)}
                )
                session.rollback()
                raise

    def get_by_id(self, id: UUID) -> Optional[ContentSourceModel]:
        with Connector() as session:
            try:
                extra = {"id": id}
                logger.debug("Fetching ContentSource by ID", context=extra)
                result = session.get(ContentSourceModel, id)
                logger.debug("Fetch successful", context={**extra, "result": result})
                return result
            except Exception as e:
                logger.error(
                    "Error fetching ContentSource by ID",
                    context={**extra, "error": str(e)},
                )
                raise

    def get_by_source_info(
        self, source_type: str, external_source: str, subject_id: Optional[UUID] = None
    ) -> List[ContentSourceModel]:
        with Connector() as session:
            try:
                extra = {
                    "source_type": source_type,
                    "external_source": external_source,
                    "subject_id": subject_id,
                }
                logger.debug("Fetching ContentSources by source info", context=extra)

                query = session.query(ContentSourceModel).filter_by(
                    source_type=source_type, external_source=external_source
                )

                if subject_id is not None:
                    query = query.filter_by(subject_id=subject_id)

                result = query.order_by(ContentSourceModel.created_at.desc()).all()

                logger.debug(
                    "Fetch successful", context={**extra, "count": len(result)}
                )
                return result
            except Exception as e:
                logger.error(
                    "Error fetching ContentSources by source info",
                    context={**extra, "error": str(e)},
                )
                raise

    def list_by_subject(
        self,
        subject_id: UUID,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[ContentSourceModel]:
        with Connector() as session:
            try:
                extra = {"subject_id": subject_id, "limit": limit, "offset": offset}
                logger.debug("Listing ContentSources by subject ID", context=extra)
                query = (
                    session.query(ContentSourceModel)
                    .filter_by(subject_id=subject_id)
                    .order_by(ContentSourceModel.created_at.desc())
                )

                if offset is not None:
                    query = query.offset(offset)
                if limit is not None:
                    query = query.limit(limit)

                result = query.all()
                logger.debug("List successful", context={**extra, "count": len(result)})
                return result
            except Exception as e:
                logger.error(
                    "Error listing ContentSources by subject ID",
                    context={**extra, "error": str(e)},
                )
                raise

    def list(
        self, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> List[ContentSourceModel]:
        with Connector() as session:
            try:
                extra = {"limit": limit, "offset": offset}
                logger.debug("Listing all ContentSources", context=extra)
                query = session.query(ContentSourceModel).order_by(
                    ContentSourceModel.created_at.desc()
                )

                if offset is not None:
                    query = query.offset(offset)
                if limit is not None:
                    query = query.limit(limit)

                result = query.all()
                logger.debug("List successful", context={**extra, "count": len(result)})
                return result
            except Exception as e:
                logger.error(
                    "Error listing all ContentSources",
                    context={**extra, "error": str(e)},
                )
                raise

    def count_by_subject(self, subject_id: UUID) -> int:
        with Connector() as session:
            try:
                extra = {"subject_id": subject_id}
                logger.debug("Counting ContentSources by subject ID", context=extra)
                result = (
                    session.query(ContentSourceModel)
                    .filter_by(subject_id=subject_id)
                    .count()
                )
                logger.debug("Count successful", context={**extra, "count": result})
                return result
            except Exception as e:
                logger.error(
                    "Error counting ContentSources by subject ID",
                    context={**extra, "error": str(e)},
                )
                raise

    def update_status(self, content_source_id: UUID, status: str) -> None:
        with Connector() as session:
            try:
                extra = {"content_source_id": content_source_id, "status": status}
                logger.debug(
                    "Updating processing status for ContentSource", context=extra
                )
                cs = session.get(ContentSourceModel, content_source_id)
                if cs is None:
                    logger.warning("ContentSource not found for update", context=extra)
                    return
                cs.processing_status = status
                session.commit()
                logger.debug("Processing status updated successfully", context=extra)
            except Exception as e:
                logger.error(
                    "Error updating processing status for ContentSource",
                    context={**extra, "error": str(e)},
                )
                session.rollback()
                raise

    def update_title(self, content_source_id: UUID, title: str) -> None:
        with Connector() as session:
            try:
                extra = {"content_source_id": content_source_id, "title": title}
                logger.debug("Updating title for ContentSource", context=extra)
                cs = session.get(ContentSourceModel, content_source_id)
                if cs is None:
                    logger.warning(
                        "ContentSource not found for title update", context=extra
                    )
                    return
                cs.title = title
                session.commit()
                logger.debug("Title updated successfully", context=extra)
            except Exception as e:
                logger.error(
                    "Error updating title for ContentSource",
                    context={**extra, "error": str(e)},
                )
                session.rollback()
                raise

    def finish_ingestion(
        self,
        content_source_id: UUID,
        embedding_model: str,
        dimensions: int,
        chunks: int,
        total_tokens: Optional[int] = None,
        max_tokens_per_chunk: Optional[int] = None,
        source_metadata: Optional[dict] = None,
    ) -> None:
        with Connector() as session:
            extra = {}
            try:
                extra = {
                    "content_source_id": content_source_id,
                    "embedding_model": embedding_model,
                    "dimensions": dimensions,
                    "chunks": chunks,
                    "total_tokens": total_tokens,
                    "max_tokens_per_chunk": max_tokens_per_chunk,
                    "source_metadata": source_metadata,
                }
                logger.debug("Finishing ingestion for ContentSource", context=extra)
                cs = session.get(ContentSourceModel, content_source_id)
                if cs is None:
                    logger.warning(
                        "ContentSource not found for finishing ingestion", context=extra
                    )
                    return

                # Explicitly update processing_status to 'done'
                cs.processing_status = "done"
                cs.ingested_at = datetime.now(timezone.utc)
                cs.embedding_model = embedding_model
                cs.dimensions = dimensions
                cs.chunks = chunks
                cs.total_tokens = total_tokens
                cs.max_tokens_per_chunk = max_tokens_per_chunk
                if source_metadata:
                    cs.source_metadata = source_metadata

                session.commit()
                logger.debug(
                    "Ingestion finished successfully",
                    context={"id": content_source_id, "new_status": "done"},
                )
            except Exception as e:
                logger.error(
                    "Error finishing ingestion for ContentSource",
                    context={**extra, "error": str(e)},
                )
                session.rollback()
                raise

    def delete(self, content_source_id: UUID) -> bool:
        """Delete a content source by ID."""
        with Connector() as session:
            try:
                extra = {"content_source_id": content_source_id}
                logger.debug("Deleting ContentSource", context=extra)
                cs = session.get(ContentSourceModel, content_source_id)
                if cs is None:
                    logger.warning(
                        "ContentSource not found for deletion", context=extra
                    )
                    return False
                session.delete(cs)
                session.commit()
                logger.debug("ContentSource deleted successfully", context=extra)
                return True
            except Exception as e:
                logger.error(
                    "Error deleting ContentSource",
                    context={**extra, "error": str(e)},
                )
                session.rollback()
                raise
