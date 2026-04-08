from datetime import datetime, timezone
from typing import Any, List, Optional, cast
from uuid import UUID

from src.config.logger import Logger
from src.infrastructure.connectors.connector_sql import Connector
from src.infrastructure.repositories.sql.models.content_source import ContentSourceModel
from src.infrastructure.repositories.sql.utils.utils import ensure_uuid

logger = Logger()
INVALID_UUID_MSG = "Invalid subject_id UUID string provided"


class ContentSourceSQLRepository:
    """Repository for content_sources table (basic CRUD helpers)."""

    def create(
        self,
        subject_id: Optional[UUID],
        source_type: str,
        external_source: str,
        **kwargs,
    ) -> UUID:
        with Connector() as session:
            extra = {}
            try:
                title = kwargs.get("title")
                language = kwargs.get("language")
                embedding_model = kwargs.get("embedding_model")
                dimensions = kwargs.get("dimensions")
                status = kwargs.get("status")
                processing_status = kwargs.get("processing_status")
                chunks = kwargs.get("chunks")
                chars = kwargs.get("chars")
                total_tokens = kwargs.get("total_tokens")
                max_tokens_per_chunk = kwargs.get("max_tokens_per_chunk")
                source_metadata = kwargs.get("source_metadata")
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
                logger.error("Error creating ContentSource", context={**extra, "error": str(e)})
                session.rollback()
                raise

    def get_by_id(self, cs_id: Any) -> Optional[ContentSourceModel]:
        cs_id = ensure_uuid(cs_id, "Invalid UUID string provided for content source")
        if cs_id is None:
            return None
        with Connector() as session:
            try:
                extra = {"id": cs_id}
                logger.debug("Fetching ContentSource by ID", context=extra)
                result = session.get(ContentSourceModel, cs_id)
                logger.debug("Fetch successful", context={**extra, "result": result})
                return result
            except Exception as e:
                logger.error(
                    "Error fetching ContentSource by ID",
                    context={**extra, "error": str(e)},
                )
                raise

    def get_by_diarization_id(self, diarization_id: str) -> Optional[ContentSourceModel]:
        """Find a ContentSource that has this diarization_id in its source_metadata JSON."""
        with Connector() as session:
            try:
                logger.debug(
                    "Fetching ContentSource by diarization_id in metadata",
                    context={"diarization_id": diarization_id},
                )
                # Search within JSON field (syntax works for SQLite and Postgres)
                # Using string comparison for the diarization_id in the JSON object
                from sqlalchemy import String, cast

                # Search within JSON field in a way that works for SQLite and Postgres
                # Using cast to String to ensure we can compare with the diarization_id
                # The ->> operator or json_extract both return values that can be cast or compared.
                result = (
                    session.query(ContentSourceModel)
                    .filter(
                        cast(ContentSourceModel.source_metadata["diarization_id"], String) == f'"{diarization_id}"'
                        if session.bind.dialect.name == "sqlite"
                        else ContentSourceModel.source_metadata["diarization_id"].astext == diarization_id
                    )
                    .first()
                )
                return result
            except Exception as e:
                logger.error(
                    "Error fetching ContentSource by diarization_id",
                    context={"diarization_id": diarization_id, "error": str(e)},
                )
                return None

    def get_by_source_info(
        self, source_type: str, external_source: str, subject_id: Optional[Any] = None
    ) -> List[ContentSourceModel]:
        subject_id = ensure_uuid(subject_id, INVALID_UUID_MSG)
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

                logger.debug("Fetch successful", context={**extra, "count": len(result)})
                return result
            except Exception as e:
                logger.error(
                    "Error fetching ContentSources by source info",
                    context={**extra, "error": str(e)},
                )
                raise

    def list_by_subject(
        self,
        subject_id: Any,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[ContentSourceModel]:
        subject_id = ensure_uuid(subject_id, INVALID_UUID_MSG)
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

    def list(self, limit: Optional[int] = None, offset: Optional[int] = None) -> List[ContentSourceModel]:
        with Connector() as session:
            try:
                extra = {"limit": limit, "offset": offset}
                logger.debug("Listing all ContentSources", context=extra)
                query = session.query(ContentSourceModel).order_by(ContentSourceModel.created_at.desc())

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

    def count_by_subject(self, subject_id: Any) -> int:
        subject_id = ensure_uuid(subject_id, INVALID_UUID_MSG)
        with Connector() as session:
            try:
                extra = {"subject_id": subject_id}
                logger.debug("Counting ContentSources by subject ID", context=extra)
                result = session.query(ContentSourceModel).filter_by(subject_id=subject_id).count()
                logger.debug("Count successful", context={**extra, "count": result})
                return result
            except Exception as e:
                logger.error(
                    "Error counting ContentSources by subject ID",
                    context={**extra, "error": str(e)},
                )
                raise

    def update_status(
        self,
        content_source_id: UUID,
        status: str,
        status_message: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        with Connector() as session:
            try:
                extra = {"content_source_id": content_source_id, "status": status}
                logger.debug("Updating processing status for ContentSource", context=extra)
                cs = session.get(ContentSourceModel, content_source_id)
                if cs is None:
                    logger.warning("ContentSource not found for update", context=extra)
                    return
                cs.processing_status = status
                if status_message is not None:
                    cs.status_message = status_message
                if error_message is not None:
                    cs.error_message = error_message
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
                    logger.warning("ContentSource not found for title update", context=extra)
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
                    logger.warning("ContentSource not found for finishing ingestion", context=extra)
                    return

                # Explicitly update processing_status to 'done'
                cs.processing_status = "done"
                cs.status_message = None
                cs.error_message = None
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

    def list_external_sources_by_subject(self, subject_id: Any, source_type: str) -> List[str]:
        """Return all external_source values for a given subject and source_type.

        Optimized query that only fetches the external_source column.
        """
        subject_id = ensure_uuid(subject_id, INVALID_UUID_MSG)
        with Connector() as session:
            try:
                rows = (
                    session.query(ContentSourceModel.external_source)
                    .filter_by(subject_id=subject_id, source_type=source_type)
                    .all()
                )
                return [row[0] for row in rows if row[0]]
            except Exception as e:
                logger.error(
                    "Error listing external sources by subject",
                    context={
                        "subject_id": subject_id,
                        "source_type": source_type,
                        "error": str(e),
                    },
                )
                raise

    def update_metadata(self, content_source_id: UUID, metadata: dict) -> None:
        with Connector() as session:
            try:
                extra = {"content_source_id": content_source_id}
                logger.debug("Updating metadata for ContentSource", context=extra)
                cs = session.get(ContentSourceModel, content_source_id)
                if cs is None:
                    logger.warning("ContentSource not found for metadata update", context=extra)
                    return
                # Merge existing metadata with new metadata
                current = dict(cs.source_metadata or {})
                current.update(metadata)
                cs.source_metadata = current
                session.commit()
                logger.debug("Metadata updated successfully", context=extra)
            except Exception as e:
                logger.error(
                    "Error updating metadata for ContentSource",
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
                    logger.warning("ContentSource not found for deletion", context=extra)
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
