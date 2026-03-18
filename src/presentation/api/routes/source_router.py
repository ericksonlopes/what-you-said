from typing import Annotated, List

from fastapi import Depends, HTTPException, APIRouter

from src.config.logger import Logger
from src.infrastructure.services.content_source_service import ContentSourceService
from src.infrastructure.services.model_loader_service import ModelLoaderService
from src.presentation.api.dependencies import get_cs_service, get_model_loader
from src.presentation.api.schemas.model_schemas import ModelInfoResponse
from src.presentation.api.schemas.source_schemas import SourceResponse

logger = Logger()
router = APIRouter()


@router.get(
    "",
    response_model=List[SourceResponse],
    responses={500: {"description": "Internal server error"}},
)
def get_sources(cs_service: Annotated[ContentSourceService, Depends(get_cs_service)]):
    """Retrieve all content sources"""
    try:
        sources = cs_service.list_all()
        return sources
    except Exception as e:
        logger.error(f"Error fetching sources: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/model",
    response_model=ModelInfoResponse,
    responses={500: {"description": "Internal server error"}},
)
def get_model_info(
    model_loader: Annotated[ModelLoaderService, Depends(get_model_loader)],
):
    """Retrieve metadata about the currently loaded embedding models"""
    try:
        return {
            "name": model_loader.model_name,
            "dimensions": model_loader.dimensions,
            "max_seq_length": model_loader.max_seq_length,
        }
    except Exception as e:
        logger.error(f"Error fetching models info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
