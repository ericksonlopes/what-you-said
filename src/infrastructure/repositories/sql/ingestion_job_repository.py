from datetime import datetime, timezone
from typing import Any, List, Optional, Union, cast
from uuid import UUID

from sqlalchemy.orm import joinedload

from src.config.logger import Logger
from src.infrastructure.connectors.connector_sql import Connector
from src.infrastructure.repositories.sql.models.ingestion_job import IngestionJobModel
from src.infrastructure.repositories.sql.utils.utils import ensure_uuid

logger = Logger()
DUPLICATE_FILTER = "%Duplicate%"
TERMINAL_STATUSES = ["finished", "failed", "error", "cancelled", "done"]


class IngestionJobSQLRepository:
    """Repository helpers for ingestion_jobs table."""

    def create_job(
        self,
        content_source_id: Optional[UUID],
        status: str = "started",
        embedding_model: Optional[str] = None,
        pipeline_version: Optional[str] = None,
        ingestion_type: Optional[str] = None,
        vector_store_type: Optional[str] = None,
        source_title: Optional[str] = None,
        external_source: Optional[str] = None,
        subject_id: Optional[Union[UUID, str]] = None,
    ) -> UUID:
        content_source_id = ensure_uuid(content_source_id)
        subject_id = ensure_uuid(subject_id)
        with Connector() as session:
            try:
                extra = {
                    "content_source_id": content_source_id,
                    "status": status,
                    "embedding_model": embedding_model,
                    "pipeline_version": pipeline_version,
                    "ingestion_type": ingestion_type,
                    "vector_store_type": vector_store_type,
                    "source_title": source_title,
                    "external_source": external_source,
                    "subject_id": subject_id,
                }
                logger.debug("Creating ingestion job", context=extra)
                job = IngestionJobModel(
                    content_source_id=content_source_id,
                    status=status,
                    embedding_model=embedding_model,
                    pipeline_version=pipeline_version,
                    ingestion_type=ingestion_type,
                    vector_store_type=vector_store_type,
                    source_title=source_title,
                    external_source=external_source,
                    subject_id=subject_id,
                )
                session.add(job)
                session.commit()
                session.refresh(job)
                logger.debug("Ingestion job created successfully", context={"job_id": job.id})

                return cast(UUID, job.id)
            except Exception as e:
                logger.error("Error creating ingestion job", context={**extra, "error": str(e)})
                session.rollback()
                raise

    def update_job(
        self,
        job_id: Any,
        status: str,
        error_message: Optional[str] = None,
        status_message: Optional[str] = None,
        current_step: Optional[int] = None,
        total_steps: Optional[int] = None,
        chunks_count: Optional[int] = None,
        source_title: Optional[str] = None,
        content_source_id: Optional[Union[UUID, str]] = None,
        ingestion_type: Optional[str] = None,
    ) -> None:
        """Update an ingestion job's status, error_message and progress info."""
        job_id_uuid = ensure_uuid(job_id)
        cs_id_uuid = ensure_uuid(content_source_id)

        if job_id_uuid is None:
            logger.warning("No job_id provided for update")
            return

        with Connector() as session:
            try:
                extra = {
                    "job_id": job_id_uuid,
                    "status": status,
                    "error_message": error_message,
                    "status_message": status_message,
                    "current_step": current_step,
                    "total_steps": total_steps,
                    "chunks_count": chunks_count,
                    "source_title": source_title,
                    "content_source_id": cs_id_uuid,
                    "ingestion_type": ingestion_type,
                }
                logger.debug("Updating ingestion job", context=extra)
                job = session.get(IngestionJobModel, job_id_uuid)
                if job is None:
                    logger.warning("Ingestion job not found", context=extra)
                    return
                # Mark finished_at as now if status is final
                if status in ["finished", "failed", "error"]:
                    job.finished_at = datetime.now(timezone.utc)

                job.status = status
                if error_message is not None:
                    job.error_message = error_message
                if status_message is not None:
                    job.status_message = status_message
                if current_step is not None:
                    job.current_step = current_step
                if total_steps is not None:
                    job.total_steps = total_steps
                if chunks_count is not None:
                    job.chunks_count = chunks_count
                if source_title is not None:
                    job.source_title = source_title
                if cs_id_uuid is not None:
                    job.content_source_id = cs_id_uuid
                if ingestion_type is not None:
                    job.ingestion_type = ingestion_type

                session.commit()
                logger.debug("Ingestion job updated successfully", context=extra)
            except Exception as e:
                logger.error("Error updating ingestion job", context={**extra, "error": str(e)})
                session.rollback()
                raise

    def link_job_to_source(
        self,
        job_id: Any,
        content_source_id: Any,
        ingestion_type: Optional[str] = None,
    ) -> None:
        """Link an existing job to a content source."""
        job_id_uuid = ensure_uuid(job_id)
        cs_id_uuid = ensure_uuid(content_source_id)

        if job_id_uuid is None or cs_id_uuid is None:
            logger.warning(
                "Cannot link job to source: missing IDs",
                context={"job_id": job_id, "content_source_id": content_source_id},
            )
            return

        with Connector() as session:
            try:
                logger.debug(
                    "Linking job to content source",
                    context={
                        "job_id": job_id_uuid,
                        "content_source_id": cs_id_uuid,
                    },
                )
                job = session.get(IngestionJobModel, job_id_uuid)
                if job:
                    job.content_source_id = cs_id_uuid
                    if ingestion_type:
                        job.ingestion_type = ingestion_type
                    session.commit()
                else:
                    logger.warning("Job not found for linking", context={"job_id": job_id})
            except Exception as e:
                logger.error(
                    "Error linking job to source",
                    context={"job_id": job_id, "error": str(e)},
                )
                session.rollback()
                raise

    def delete(self, job_id: Any) -> bool:
        """Delete an ingestion job by ID."""
        job_id_uuid = ensure_uuid(job_id)
        if not job_id_uuid:
            return False
        with Connector() as session:
            try:
                job = session.get(IngestionJobModel, job_id_uuid)
                if not job:
                    return False
                session.delete(job)
                session.commit()
                return True
            except Exception as e:
                logger.error(
                    "Error deleting ingestion job",
                    context={"job_id": job_id, "error": str(e)},
                )
                session.rollback()
                raise

    def get_by_id(self, job_id: Any) -> Optional[IngestionJobModel]:
        job_id = ensure_uuid(job_id)
        with Connector() as session:
            try:
                extra = {"job_id": job_id}
                logger.debug("Fetching ingestion job by ID", context=extra)
                result = (
                    session.query(IngestionJobModel)
                    .options(joinedload(IngestionJobModel.content_source))
                    .filter(IngestionJobModel.id == job_id)
                    .first()
                )
                logger.debug("Fetch successful", context={**extra, "result": result})
                return result
            except Exception as e:
                logger.error(
                    "Error fetching ingestion job by ID",
                    context={**extra, "error": str(e)},
                )
                raise

    def list_recent_jobs(self, limit: int = 50, offset: int = 0) -> List[IngestionJobModel]:
        """Backward compatible list_recent_jobs with offset support."""
        return self.list_jobs(limit=limit, offset=offset)

    def list_jobs(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[IngestionJobModel]:
        with Connector() as session:
            try:
                logger.debug(
                    "Listing ingestion jobs with pagination/filters",
                    context={
                        "limit": limit,
                        "offset": offset,
                        "status": status,
                        "search": search,
                    },
                )
                query = session.query(IngestionJobModel).options(joinedload(IngestionJobModel.content_source))

                if status:
                    if status == "processing":
                        query = query.filter(IngestionJobModel.status.in_(["processing", "started"]))
                    elif status == "completed":
                        query = query.filter(IngestionJobModel.status.in_(["done", "finished"]))
                    elif status == "failed":
                        # Exclude Duplicates from Failed
                        query = query.filter(
                            IngestionJobModel.status.in_(["failed", "error"]),
                            (IngestionJobModel.error_message.is_(None))
                            | (~IngestionJobModel.error_message.ilike(DUPLICATE_FILTER)),
                        )
                    elif status == "cancelled":
                        # Include Duplicates in Cancelled
                        query = query.filter(
                            (IngestionJobModel.status == "cancelled")
                            | (IngestionJobModel.error_message.ilike(DUPLICATE_FILTER))
                        )
                    else:
                        query = query.filter(IngestionJobModel.status == status)

                if search:
                    search_term = f"%{search}%"
                    query = query.filter(
                        (IngestionJobModel.source_title.ilike(search_term))
                        | (IngestionJobModel.status_message.ilike(search_term))
                        | (IngestionJobModel.external_source.ilike(search_term))
                    )

                result = query.order_by(IngestionJobModel.created_at.desc()).limit(limit).offset(offset).all()
                return result
            except Exception as e:
                logger.error("Error listing ingestion jobs", context={"error": str(e)})
                raise

    def count_jobs(self, status: Optional[str] = None, search: Optional[str] = None) -> int:
        with Connector() as session:
            try:
                query = session.query(IngestionJobModel)

                if status:
                    if status == "processing":
                        query = query.filter(IngestionJobModel.status.in_(["processing", "started"]))
                    elif status == "completed":
                        query = query.filter(IngestionJobModel.status.in_(["done", "finished"]))
                    elif status == "failed":
                        # Exclude Duplicates from Failed
                        query = query.filter(
                            IngestionJobModel.status.in_(["failed", "error"]),
                            (IngestionJobModel.error_message.is_(None))
                            | (~IngestionJobModel.error_message.ilike("%Duplicate%")),
                        )
                    elif status == "cancelled":
                        # Include Duplicates in Cancelled
                        query = query.filter(
                            (IngestionJobModel.status == "cancelled")
                            | (IngestionJobModel.error_message.ilike("%Duplicate%"))
                        )
                    else:
                        query = query.filter(IngestionJobModel.status == status)

                if search:
                    search_term = f"%{search}%"
                    query = query.filter(
                        (IngestionJobModel.source_title.ilike(search_term))
                        | (IngestionJobModel.status_message.ilike(search_term))
                        | (IngestionJobModel.external_source.ilike(search_term))
                    )

                return query.count()
            except Exception as e:
                logger.error("Error counting ingestion jobs", context={"error": str(e)})
                raise

    def get_status_counts(self, search: Optional[str] = None) -> dict:
        with Connector() as session:
            try:
                # We reuse the search logic if provided
                base_query = session.query(IngestionJobModel)
                if search:
                    search_term = f"%{search}%"
                    base_query = base_query.filter(
                        (IngestionJobModel.source_title.ilike(search_term))
                        | (IngestionJobModel.status_message.ilike(search_term))
                        | (IngestionJobModel.external_source.ilike(search_term))
                    )

                total = base_query.count()
                processing = base_query.filter(IngestionJobModel.status.in_(["processing", "started"])).count()
                completed = base_query.filter(IngestionJobModel.status.in_(["done", "finished"])).count()

                # Treat "Duplicate" errors as CANCELLED
                duplicate_filter = IngestionJobModel.error_message.ilike(DUPLICATE_FILTER)
                not_duplicate_filter = (IngestionJobModel.error_message.is_(None)) | (~duplicate_filter)

                failed = base_query.filter(
                    IngestionJobModel.status.in_(["failed", "error"]),
                    not_duplicate_filter,
                ).count()

                cancelled = base_query.filter((IngestionJobModel.status == "cancelled") | duplicate_filter).count()

                return {
                    "total": total,
                    "processing": processing,
                    "completed": completed,
                    "failed": failed,
                    "cancelled": cancelled,
                }
            except Exception as e:
                logger.error("Error getting status counts", context={"error": str(e)})
                raise

    def list_recent_jobs_by_subject(self, subject_id: Any, limit: int = 50, offset: int = 0) -> List[IngestionJobModel]:
        subject_id = ensure_uuid(subject_id)
        from src.infrastructure.repositories.sql.models.content_source import (
            ContentSourceModel,
        )

        with Connector() as session:
            try:
                logger.debug(
                    "Listing recent jobs by subject",
                    context={"subject_id": subject_id, "limit": limit},
                )
                result = (
                    session.query(IngestionJobModel)
                    .options(joinedload(IngestionJobModel.content_source))
                    .join(
                        ContentSourceModel,
                        IngestionJobModel.content_source_id == ContentSourceModel.id,
                    )
                    .filter(ContentSourceModel.subject_id == subject_id)
                    .order_by(IngestionJobModel.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                    .all()
                )
                return result
            except Exception as e:
                logger.error(
                    "Error listing jobs by subject",
                    context={"subject_id": subject_id, "error": str(e)},
                )
                raise

    def list_by_content_source(self, content_source_id: Any) -> List[IngestionJobModel]:
        content_source_id = ensure_uuid(content_source_id)
        with Connector() as session:
            try:
                extra = {"content_source_id": content_source_id}
                logger.debug("Listing ingestion jobs by content source ID", context=extra)
                result = session.query(IngestionJobModel).filter_by(content_source_id=content_source_id).all()
                logger.debug("List successful", context={**extra, "count": len(result)})
                return result
            except Exception as e:
                logger.error(
                    "Error listing ingestion jobs by content source ID",
                    context={**extra, "error": str(e)},
                )
                raise

    def mark_previous_jobs_as_reprocessed(self, content_source_id: Any, current_job_id: Any) -> int:
        content_source_id = ensure_uuid(content_source_id)
        current_job_id = ensure_uuid(current_job_id)
        """Mark all previous jobs for a content source as REPROCESSED."""
        from src.infrastructure.repositories.sql.models.ingestion_job import (
            IngestionJobModel,
        )

        with Connector() as session:
            try:
                logger.debug(
                    "Marking previous jobs as reprocessed",
                    context={
                        "content_source_id": content_source_id,
                        "current_job_id": current_job_id,
                    },
                )
                # Final states that should be marked as reprocessed
                # terminal_statuses removed in favor of TERMINAL_STATUSES

                # Update jobs
                updated_count = (
                    session.query(IngestionJobModel)
                    .filter(IngestionJobModel.content_source_id == content_source_id)
                    .filter(IngestionJobModel.id != current_job_id)
                    .filter(IngestionJobModel.status.in_(TERMINAL_STATUSES))
                    .update({"status": "reprocessed"}, synchronize_session=False)
                )

                session.commit()
                logger.info(
                    "Marked jobs as reprocessed",
                    context={
                        "content_source_id": str(content_source_id),
                        "updated_count": updated_count,
                    },
                )
                return updated_count
            except Exception as e:
                logger.error(
                    "Error marking previous jobs as reprocessed",
                    context={"content_source_id": content_source_id, "error": str(e)},
                )
                session.rollback()
                raise
