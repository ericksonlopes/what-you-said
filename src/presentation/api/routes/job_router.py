from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.config.logger import Logger
from src.infrastructure.services.ingestion_job_service import IngestionJobService
from src.presentation.api.dependencies import get_job_service
from src.presentation.api.schemas.job_schemas import PaginatedJobsResponse

logger = Logger()
router = APIRouter()


@router.get(
    "",
    response_model=PaginatedJobsResponse,
    responses={500: {"description": "Internal server error"}},
)
def get_jobs(
    job_service: Annotated[IngestionJobService, Depends(get_job_service)],
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
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
        raise HTTPException(status_code=500, detail="Internal server error")
