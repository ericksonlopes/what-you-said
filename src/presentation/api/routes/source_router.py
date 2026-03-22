from typing import Annotated, List

from fastapi import Depends, HTTPException, APIRouter

from src.config.logger import Logger
from src.infrastructure.services.content_source_service import ContentSourceService
from src.infrastructure.services.model_loader_service import ModelLoaderService
from src.presentation.api.dependencies import (
    get_cs_service,
    get_model_loader,
    get_content_source_use_case,
)
from src.domain.entities.enums.source_type_enum_entity import SourceType
from src.application.use_cases.content_source_use_case import ContentSourceUseCase
from src.presentation.api.schemas.model_schemas import ModelInfoResponse
from src.presentation.api.schemas.source_schemas import SourceResponse, SourceUpdate


logger = Logger()
router = APIRouter()


@router.patch("/{id}", responses={404: {"description": "Source not found"}})
def update_source_title(
    id: str,
    update: SourceUpdate,
    cs_service: Annotated[ContentSourceService, Depends(get_cs_service)],
):
    """Update a content source title."""
    try:
        import uuid

        source_id = uuid.UUID(id)
        source = cs_service.get_by_id(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Content source not found")

        cs_service.update_title(source_id, update.title)
        return {"success": True, "message": f"Source {id} title updated successfully"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, context={"action": "update_source_title", "source_id": id})
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types", response_model=List[str])
def get_source_types():
    """Retrieve all available source types from the Enum"""
    return [source.value for source in SourceType]


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
        logger.error(e, context={"action": "list_sources"})
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
        logger.error(e, context={"action": "get_model_info"})
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{id}", responses={404: {"description": "Source not found"}})
def delete_source(
    id: str,
    use_case: Annotated[ContentSourceUseCase, Depends(get_content_source_use_case)],
):
    """Delete a content source and all its related data (chunks, embeddings)."""
    try:
        import uuid

        source_id = uuid.UUID(id)
        success = use_case.delete(source_id)
        if not success:
            raise HTTPException(status_code=404, detail="Content source not found")
        return {"success": True, "message": f"Source {id} deleted successfully"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, context={"action": "delete_source", "source_id": id})
        raise HTTPException(status_code=500, detail=str(e))
