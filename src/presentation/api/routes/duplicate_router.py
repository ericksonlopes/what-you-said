from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from src.infrastructure.services.chunk_duplicate_service import ChunkDuplicateService
from src.infrastructure.services.chunk_index_service import ChunkIndexService
from src.presentation.api.dependencies import (
    get_chunk_index_service,
    get_current_user,
    get_duplicate_service,
)
from src.presentation.api.schemas.duplicate_schemas import (
    ChunkDuplicateResponse,
    ChunkDuplicateStatusUpdate,
    ChunkMinimal,
    PaginatedChunkDuplicateResponse,
)

router = APIRouter(tags=["duplicates"])


@router.get("", response_model=PaginatedChunkDuplicateResponse)
def list_duplicates(
    status: Optional[str] = None,
    subject_id: Optional[List[str]] = Query(None),
    limit: int = 100,
    offset: int = 0,
    service: ChunkDuplicateService = Depends(get_duplicate_service),
    chunk_service: ChunkIndexService = Depends(get_chunk_index_service),
    user=Depends(get_current_user),
):
    """List all detected chunk duplicate groups."""
    entities, total = service.list_duplicates(status=status, subject_ids=subject_id, limit=limit, offset=offset)
    
    # Enrich entities with chunk content if needed for UI
    results = []
    for entity in entities:
        resp = ChunkDuplicateResponse.model_validate(entity)
        chunks_info = []
        for cid in entity.chunk_ids:
            chunk = chunk_service.get_by_id(cid)
            if chunk:
                chunks_info.append(ChunkMinimal(
                    id=chunk.id,
                    content=chunk.content or "",
                    source_title=chunk.extra.get("source_title", "Unknown"),
                    source_id=chunk.content_source_id
                ))
        resp.chunks = chunks_info
        results.append(resp)
        
    return PaginatedChunkDuplicateResponse(results=results, total=total)


@router.patch("/{duplicate_id}/status")
def update_duplicate_status(
    duplicate_id: UUID,
    cmd: ChunkDuplicateStatusUpdate,
    service: ChunkDuplicateService = Depends(get_duplicate_service),
    user=Depends(get_current_user),
):
    """Update the resolution status of a duplicate group."""
    success = service.resolve_duplicate(duplicate_id, cmd.status)
    if not success:
        raise HTTPException(status_code=404, detail="Duplicate group not found")
    return {"status": "success"}


@router.post("/chunks/{chunk_id}/deactivate")
def deactivate_chunk(
    chunk_id: UUID,
    service: ChunkDuplicateService = Depends(get_duplicate_service),
    user=Depends(get_current_user),
):
    """Deactivate a specific chunk (soft delete from RAG)."""
    success = service.deactivate_chunk(chunk_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chunk not found")
    return {"status": "success"}


@router.post("/analyze-all")
def analyze_all_chunks(
    service: ChunkDuplicateService = Depends(get_duplicate_service),
    chunk_service: ChunkIndexService = Depends(get_chunk_index_service),
    user=Depends(get_current_user),
):
    """Run duplicate detection analysis on all existing chunks (heavy operation)."""
    # This should probably be a background task, but for now we'll do it synchronously
    # or just list everything and iterate
    all_chunks = chunk_service.list_chunks(limit=1000) # Limit for safety
    chunk_ids = [c.id for c in all_chunks]
    
    count = service.find_and_register_duplicates(chunk_ids)
    return {"status": "success", "groups_found": count}
