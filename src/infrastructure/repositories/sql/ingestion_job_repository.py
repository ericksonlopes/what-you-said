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
                   embedding_model: Optional[str] = None, pipeline_version: Optional[str] = None) -> UUID:
        with Connector() as session:
            try:
                extra = {"content_source_id": content_source_id, "status": status, "embedding_model": embedding_model,
                         "pipeline_version": pipeline_version}
                logger.info("Creating ingestion job", context=extra)
                job = IngestionJobModel(
                    content_source_id=content_source_id,
                    status=status,
                    embedding_model=embedding_model,
                    pipeline_version=pipeline_version,
                )
                session.add(job)
                session.commit()
                session.refresh(job)
                logger.info("Ingestion job created successfully", context={"job_id": job.id})

                return cast(UUID, job.id)
            except Exception as e:
                logger.error("Error creating ingestion job", context={**extra, "error": str(e)})
                session.rollback()
                raise

    def update_job(self, job_id: UUID, status: str, error_message: Optional[str] = None) -> None:
        """Update an ingestion job's status, error_message and optionally chunks_count.

        This replaces the previous `finish_job` behavior and will set finished_at to now when called.
        """
        with Connector() as session:
            try:
                extra = {"job_id": job_id, "status": status, "error_message": error_message}
                logger.info("Updating ingestion job", context=extra)
                job = session.get(IngestionJobModel, job_id)
                if job is None:
                    logger.warning("Ingestion job not found", context=extra)
                    return
                # Mark finished_at as now in this update to mirror previous finish_job behavior
                job.finished_at = datetime.now(timezone.utc)
                job.status = status
                job.error_message = error_message
                
                session.commit()
                logger.info("Ingestion job updated successfully", context=extra)
            except Exception as e:
                logger.error("Error updating ingestion job", context={**extra, "error": str(e)})
                session.rollback()
                raise

    def get_by_id(self, job_id: UUID) -> Optional[IngestionJobModel]:
        with Connector() as session:
            try:
                extra = {"job_id": job_id}
                logger.info("Fetching ingestion job by ID", context=extra)
                result = session.get(IngestionJobModel, job_id)
                logger.info("Fetch successful", context={**extra, "result": result})
                return result
            except Exception as e:
                logger.error("Error fetching ingestion job by ID", context={**extra, "error": str(e)})
                raise

    def list_by_content_source(self, content_source_id: UUID) -> List[IngestionJobModel]:
        with Connector() as session:
            try:
                extra = {"content_source_id": content_source_id}
                logger.info("Listing ingestion jobs by content source ID", context=extra)
                result = session.query(IngestionJobModel).filter_by(content_source_id=content_source_id).all()
                logger.info("List successful", context={**extra, "count": len(result)})
                return result
            except Exception as e:
                logger.error("Error listing ingestion jobs by content source ID", context={**extra, "error": str(e)})
                raise
