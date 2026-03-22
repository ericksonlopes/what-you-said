from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException

from src.application.use_cases.search_use_case import SearchUseCase
from src.config.logger import Logger
from src.presentation.api.dependencies import get_search_chunks_use_case
from src.presentation.api.schemas.search_schemas import SearchRequest, SearchResponse

logger = Logger()
router = APIRouter()


@router.post(
    "",
    response_model=SearchResponse,
    responses={
        400: {"description": "Validation error or invalid query"},
        500: {"description": "Internal server error during search"},
    },
)
def search_chunks(
    request: Annotated[SearchRequest, Body()],
    use_case: Annotated[SearchUseCase, Depends(get_search_chunks_use_case)],
):
    """
    Search for chunks of knowledge based on a query string.
    """
    logger.info("API request to search chunks", context={"query": request.query})

    try:
        result = use_case.execute(
            query=request.query,
            top_k=request.top_k,
            subject_id=request.subject_id,
            subject_name=request.subject_name,
            search_mode=request.search_mode,
            re_rank=request.re_rank,
        )
        return result
    except ValueError as ve:
        logger.warning("Validation error in search", context={"error": str(ve)})
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(e, context={"action": "search_chunks"})
        raise HTTPException(status_code=500, detail="Internal server error")
