from typing import Annotated, Optional, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.config.logger import Logger
from src.domain.entities.user import User
from src.domain.interfaces.services.i_task_queue import ITaskQueue
from src.infrastructure.repositories.sql.content_source_repository import (
    ContentSourceSQLRepository,
)
from src.infrastructure.repositories.sql.ingestion_job_repository import (
    IngestionJobSQLRepository,
)
from src.infrastructure.services.ingestion_job_service import IngestionJobService
from src.presentation.api.dependencies import (
    get_current_user,
    get_db,
    get_job_repo,
    get_job_service,
    get_source_repo,
    get_task_queue_service,
)
from src.presentation.api.schemas.job_schemas import PaginatedJobsResponse

logger = Logger()
router = APIRouter()

INTERNAL_SERVER_ERROR = "Internal server error"


@router.get(
    "",
    response_model=PaginatedJobsResponse,
    responses={500: {"description": "Internal server error"}},
)
def get_jobs(
    job_service: Annotated[IngestionJobService, Depends(get_job_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 12,
    status: Annotated[Optional[str], Query()] = None,
    search: Annotated[Optional[str], Query()] = None,
):
    """Retrieve ingestion jobs with pagination and filtering"""
    try:
        offset = (page - 1) * page_size
        result = job_service.list_jobs(
            limit=page_size, offset=offset, status=status, search=search
        )
        return PaginatedJobsResponse(
            items=result["jobs"],
            total=result["total"],
            page=page,
            page_size=page_size,
            stats=result["stats"],
        )
    except Exception as e:
        logger.error(
            e, context={"action": "list_jobs", "page": page, "page_size": page_size}
        )
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR)


@router.get(
    "/queue/raw",
    responses={500: {"description": "Internal server error"}},
)
def get_raw_queue(
    task_queue: Annotated[ITaskQueue, Depends(get_task_queue_service)],
    user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    """Retrieve raw pending tasks from the Redis queue"""
    try:
        return task_queue.peek_queue(limit=limit)
    except Exception as e:
        logger.error(e, context={"action": "get_raw_queue"})
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR)


@router.delete("/queue")
def clear_raw_queue(
    task_queue: Annotated[ITaskQueue, Depends(get_task_queue_service)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Clear all pending tasks from the Redis queue"""
    try:
        task_queue.clear_queue()
        return {"status": "success", "message": "Queue cleared"}
    except Exception as e:
        logger.error(e, context={"action": "clear_raw_queue"})
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR)


@router.delete("/queue/{index}")
def remove_task_from_queue(
    index: int,
    task_queue: Annotated[ITaskQueue, Depends(get_task_queue_service)],
    job_repo: Annotated[IngestionJobSQLRepository, Depends(get_job_repo)],
    source_repo: Annotated[ContentSourceSQLRepository, Depends(get_source_repo)],
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Remove a specific task from the Redis queue and perform cascade deletion of SQL records."""
    try:
        # 1. Remove from Redis and get task data
        task_data = task_queue.remove_task_by_index(index)
        if not task_data:
            return {
                "status": "success",
                "message": f"Task at index {index} was already removed or not found",
            }

        # 2. Extract context for cascade deletion
        args = task_data.get("args", [])
        if not args:
            return {
                "status": "success",
                "message": "Task removed, no associated records to clean up",
            }

        command_data = args[0]
        if not isinstance(command_data, dict):
            return {"status": "success", "message": "Task removed."}

        # --- CASCADE LOGIC ---
        from src.infrastructure.repositories.sql.diarization_repository import (
            DiarizationRepository,
        )

        diarization_repo = DiarizationRepository(db)

        # A) DIARIZATION CASCADE
        diarization_id = command_data.get("diarization_id")
        if diarization_id:
            logger.info(
                "Cascade deleting Diarization record",
                context={"diarization_id": diarization_id},
            )
            diarization_repo.delete(diarization_id)

        # B) INGESTION CASCADE
        job_id = command_data.get("ingestion_job_id")
        if job_id:
            logger.info("Cascade deleting Ingestion Job", context={"job_id": job_id})
            # Get job to check for ContentSource
            job_record = job_repo.get_by_id(job_id)
            if job_record and job_record.content_source_id:
                # Only delete source if it's still in a "non-done" state AND likely created for this job
                # (Or if the user simply wants it gone)
                source_id = cast(UUID, job_record.content_source_id)
                cs = source_repo.get_by_id(source_id)
                if cs and cs.processing_status in [
                    "pending",
                    "processing",
                    "failed",
                    "cancelled",
                ]:
                    logger.info(
                        "Cascade deleting associated Content Source",
                        context={"source_id": source_id},
                    )
                    source_repo.delete(source_id)

            # Delete the job itself
            job_repo.delete(job_id)

        return {"status": "success", "message": "Task removed and records cleaned up."}
    except Exception as e:
        logger.error(e, context={"action": "remove_task_from_queue", "index": index})
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR)
