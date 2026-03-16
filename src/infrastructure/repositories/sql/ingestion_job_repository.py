from datetime import datetime, timezone
from typing import Optional, List
from typing import cast
from uuid import UUID

from src.config.logger import Logger
from src.infrastructure.repositories.sql.connector import Connector
from src.infrastructure.repositories.sql.models.ingestion_job import IngestionJobModel

logger = Logger()


class IngestionJobSQLRepository:
    """Repository helpers for ingestion_jobs table."""

    def create_job(self, content_source_id: Optional[UUID], status: str = "started",
                   embedding_model: Optional[str] = None, pipeline_version: Optional[str] = None,
                   ingestion_type: Optional[str] = None) -> UUID:
        with Connector() as session:
            try:
                extra = {"content_source_id": content_source_id, "status": status, "embedding_model": embedding_model,
                         "pipeline_version": pipeline_version, "ingestion_type": ingestion_type}
                logger.debug("Creating ingestion job", context=extra)
                job = IngestionJobModel(
                    content_source_id=content_source_id,
                    status=status,
                    embedding_model=embedding_model,
                    pipeline_version=pipeline_version,
                    ingestion_type=ingestion_type
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

    def update_job(self, job_id: UUID, status: str, error_message: Optional[str] = None, 
                   status_message: Optional[str] = None, current_step: Optional[int] = None, 
                   total_steps: Optional[int] = None, chunks_count: Optional[int] = None) -> None:
        """Update an ingestion job's status, error_message and progress info."""
        with Connector() as session:
            try:
                extra = {"job_id": job_id, "status": status, "error_message": error_message, 
                         "status_message": status_message, "current_step": current_step, "total_steps": total_steps,
                         "chunks_count": chunks_count}
                logger.debug("Updating ingestion job", context=extra)
                job = session.get(IngestionJobModel, job_id)
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
                
                session.commit()
                logger.debug("Ingestion job updated successfully", context=extra)
            except Exception as e:
                logger.error("Error updating ingestion job", context={**extra, "error": str(e)})
                session.rollback()
                raise

    def link_job_to_source(self, job_id: UUID, content_source_id: UUID) -> None:
        """Link an existing job to a content source."""
        with Connector() as session:
            try:
                logger.debug("Linking job to content source", context={"job_id": job_id, "content_source_id": content_source_id})
                job = session.get(IngestionJobModel, job_id)
                if job:
                    job.content_source_id = content_source_id
                    session.commit()
                else:
                    logger.warning("Job not found for linking", context={"job_id": job_id})
            except Exception as e:
                logger.error("Error linking job to source", context={"job_id": job_id, "error": str(e)})
                session.rollback()
                raise

    def get_by_id(self, job_id: UUID) -> Optional[IngestionJobModel]:
        with Connector() as session:
            try:
                extra = {"job_id": job_id}
                logger.debug("Fetching ingestion job by ID", context=extra)
                result = session.get(IngestionJobModel, job_id)
                logger.debug("Fetch successful", context={**extra, "result": result})
                return result
            except Exception as e:
                logger.error("Error fetching ingestion job by ID", context={**extra, "error": str(e)})
                raise

    def list_recent_jobs(self, limit: int = 50) -> List[IngestionJobModel]:
        with Connector() as session:
            try:
                logger.debug("Listing recent ingestion jobs", context={"limit": limit})
                result = session.query(IngestionJobModel).order_by(IngestionJobModel.created_at.desc()).limit(limit).all()
                return result
            except Exception as e:
                logger.error("Error listing recent ingestion jobs", context={"error": str(e)})
                raise

    def list_recent_jobs_by_subject(self, subject_id: UUID, limit: int = 50) -> List[IngestionJobModel]:
        from src.infrastructure.repositories.sql.models.content_source import ContentSourceModel
        with Connector() as session:
            try:
                logger.debug("Listing recent jobs by subject", context={"subject_id": subject_id, "limit": limit})
                result = (
                    session.query(IngestionJobModel)
                    .join(ContentSourceModel, IngestionJobModel.content_source_id == ContentSourceModel.id)
                    .filter(ContentSourceModel.subject_id == subject_id)
                    .order_by(IngestionJobModel.created_at.desc())
                    .limit(limit)
                    .all()
                )
                return result
            except Exception as e:
                logger.error("Error listing jobs by subject", context={"subject_id": subject_id, "error": str(e)})
                raise

    def list_by_content_source(self, content_source_id: UUID) -> List[IngestionJobModel]:
        with Connector() as session:
            try:
                extra = {"content_source_id": content_source_id}
                logger.debug("Listing ingestion jobs by content source ID", context=extra)
                result = session.query(IngestionJobModel).filter_by(content_source_id=content_source_id).all()
                logger.debug("List successful", context={**extra, "count": len(result)})
                return result
            except Exception as e:
                logger.error("Error listing ingestion jobs by content source ID", context={**extra, "error": str(e)})
                raise
