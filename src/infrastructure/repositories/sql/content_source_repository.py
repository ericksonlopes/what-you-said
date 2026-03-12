from datetime import datetime, timezone
from typing import Optional, List
from typing import cast
from uuid import UUID

from src.config.logger import Logger
from src.domain.entities.content_source_status_enum import ContentSourceStatus
from src.infrastructure.repositories.sql.connector import Connector
from src.infrastructure.repositories.sql.models.content_source import ContentSourceModel

logger = Logger()


class ContentSourceSQLRepository:
    """Repository for content_sources table (basic CRUD helpers)."""

    def create(self, subject_id: Optional[UUID], source_type: str, external_source: str,
               title: Optional[str] = None, language: Optional[str] = None,
               embedding_model: Optional[str] = None, dimensions: Optional[int] = None,
               status: Optional[str] = None, chunks: Optional[int] = None, chars: Optional[int] = None) -> UUID:
        with Connector() as session:
            try:
                extra = {"subject_id": subject_id, "source_type": source_type, "external_source": external_source,
                         "title": title, "language": language, "embedding_model": embedding_model,
                         "dimensions": dimensions, "status": status, "chunks": chunks, "chars": chars}
                logger.info("Creating ContentSource", context=extra)
                cs = ContentSourceModel(
                    subject_id=subject_id,
                    source_type=source_type,
                    external_source=external_source,
                    title=title,
                    language=language,
                    embedding_model=embedding_model,
                    dimensions=dimensions,
                    status=status or "active",
                    chunks=chunks or 0
                )
                session.add(cs)
                session.commit()
                session.refresh(cs)
                logger.info("ContentSource created successfully", context={"id": cs.id})

                return cast(UUID, cs.id)
            except Exception as e:
                logger.error("Error creating ContentSource", context={**extra, "error": str(e)})
                session.rollback()
                raise

    def get_by_id(self, id: UUID) -> Optional[ContentSourceModel]:
        with Connector() as session:
            try:
                extra = {"id": id}
                logger.info("Fetching ContentSource by ID", context=extra)
                result = session.get(ContentSourceModel, id)
                logger.info("Fetch successful", context={**extra, "result": result})
                return result
            except Exception as e:
                logger.error("Error fetching ContentSource by ID", context={**extra, "error": str(e)})
                raise

    def get_by_source_info(self, source_type: str, external_source: str) -> List[ContentSourceModel]:
        with Connector() as session:
            try:
                extra = {"source_type": source_type, "external_source": external_source}
                logger.info("Fetching ContentSources by source info", context=extra)
                result = session.query(ContentSourceModel).filter_by(source_type=source_type, external_source=external_source).all()
                logger.info("Fetch successful", context={**extra, "count": len(result)})
                return result
            except Exception as e:
                logger.error("Error fetching ContentSources by source info", context={**extra, "error": str(e)})
                raise

    def list_by_subject(self, subject_id: UUID) -> List[ContentSourceModel]:
        with Connector() as session:
            try:
                extra = {"subject_id": subject_id}
                logger.info("Listing ContentSources by subject ID", context=extra)
                result = session.query(ContentSourceModel).filter_by(subject_id=subject_id).all()
                logger.info("List successful", context={**extra, "count": len(result)})
                return result
            except Exception as e:
                logger.error("Error listing ContentSources by subject ID", context={**extra, "error": str(e)})
                raise

    def update_status(self, content_source_id: UUID, status: str) -> None:
        with Connector() as session:
            try:
                extra = {"content_source_id": content_source_id, "status": status}
                logger.info("Updating processing status for ContentSource", context=extra)
                cs = session.get(ContentSourceModel, content_source_id)
                if cs is None:
                    logger.warning("ContentSource not found for update", context=extra)
                    return
                cs.processing_status = status
                session.commit()
                logger.info("Processing status updated successfully", context=extra)
            except Exception as e:
                logger.error("Error updating processing status for ContentSource", context={**extra, "error": str(e)})
                session.rollback()
                raise

    def finish_ingestion(self, content_source_id: UUID, embedding_model: str, dimensions: int, chunks: int) -> None:
        with Connector() as session:
            try:
                extra = {"content_source_id": content_source_id, "embedding_model": embedding_model,
                         "dimensions": dimensions, "chunks": chunks}
                logger.info("Finishing ingestion for ContentSource", context=extra)
                cs = session.get(ContentSourceModel, content_source_id)
                if cs is None:
                    logger.warning("ContentSource not found for finishing ingestion", context=extra)
                    return
                cs.processing_status = ContentSourceStatus.DONE.value
                cs.ingested_at = datetime.now(timezone.utc)
                cs.embedding_model = embedding_model
                cs.dimensions = dimensions
                cs.chunks = chunks
                session.commit()
                logger.info("Ingestion finished successfully", context=extra)
            except Exception as e:
                logger.error("Error finishing ingestion for ContentSource", context={**extra, "error": str(e)})
                session.rollback()
                raise
