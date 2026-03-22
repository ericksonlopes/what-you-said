from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Body

from src.config.logger import Logger
from src.infrastructure.services.chunk_index_service import ChunkIndexService
from src.infrastructure.services.chunk_vector_service import ChunkVectorService
from src.presentation.api.dependencies import (
    get_chunk_index_service,
    get_chunk_vector_service,
)
from src.presentation.api.schemas.chunk_schemas import ChunkResponse, ChunkUpdate

logger = Logger()
router = APIRouter()


@router.get(
    "",
    response_model=List[ChunkResponse],
    responses={500: {"description": "Internal server error"}},
)
def get_chunks(
    chunk_service: Annotated[ChunkIndexService, Depends(get_chunk_index_service)],
    source_id: Annotated[Optional[UUID], Query()] = None,
    q: Annotated[Optional[str], Query()] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Retrieve text chunks with optional filtering by source or search query"""
    try:
        chunks = chunk_service.list_chunks(
            limit=limit, offset=offset, source_id=source_id, search_query=q
        )
        return chunks
    except Exception as e:
        logger.error(e, context={"action": "list_chunks"})
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch(
    "/{chunk_id}",
    response_model=bool,
    responses={
        404: {"description": "Chunk not found"},
        500: {"description": "Internal server error"},
    },
)
def update_chunk(
    chunk_id: UUID,
    update_data: Annotated[ChunkUpdate, Body()],
    chunk_service: Annotated[ChunkIndexService, Depends(get_chunk_index_service)],
    vector_service: Annotated[ChunkVectorService, Depends(get_chunk_vector_service)],
):
    """Update an individual chunk's content in both SQL and Vector store."""
    logger.info("API request to update chunk", context={"chunk_id": str(chunk_id)})

    try:
        # 1. Get current chunk from SQL to get full metadata
        entity = chunk_service.get_by_id(chunk_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Chunk not found")

        # 2. Update SQL
        success = chunk_service.update_chunk(chunk_id, update_data.content)
        if not success:
            raise HTTPException(status_code=404, detail="Failed to update chunk in SQL")

        # 3. Update Vector Store (Delete old, index new)
        # Update entity content for re-indexing
        entity.content = update_data.content

        # Re-indexing requires deleting by ID first then adding
        vector_service.delete_by_id(chunk_id)
        vector_service.index_documents([entity])

        logger.info("Chunk updated successfully", context={"chunk_id": str(chunk_id)})
        return True
    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, context={"action": "update_chunk", "chunk_id": str(chunk_id)})
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{chunk_id}",
    responses={
        204: {"description": "Chunk deleted successfully"},
        404: {"description": "Chunk not found"},
        500: {"description": "Internal server error"},
    },
)
def delete_chunk(
    chunk_id: UUID,
    chunk_service: Annotated[ChunkIndexService, Depends(get_chunk_index_service)],
    vector_service: Annotated[ChunkVectorService, Depends(get_chunk_vector_service)],
):
    """Delete an individual chunk from both SQL and Vector store."""
    logger.info("API request to delete chunk", context={"chunk_id": str(chunk_id)})

    try:
        # 1. Delete from SQL
        success = chunk_service.delete_chunk(chunk_id)
        if not success:
            raise HTTPException(status_code=404, detail="Chunk not found in SQL")

        # 2. Delete from Vector Store
        vector_service.delete_by_id(chunk_id)

        logger.info("Chunk deleted successfully", context={"chunk_id": str(chunk_id)})
        return None  # FastAPI returns 200 OK by default with null content, or use Response(status_code=204)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(e, context={"action": "delete_chunk", "chunk_id": str(chunk_id)})
        raise HTTPException(status_code=500, detail=str(e))
