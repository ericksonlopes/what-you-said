from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ChunkMinimal(BaseModel):
    id: UUID
    content: str
    source_title: Optional[str] = None
    source_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


class ChunkDuplicateResponse(BaseModel):
    id: UUID
    chunk_ids: List[UUID]
    chunks: Optional[List[ChunkMinimal]] = None  # Enriched chunks for UI
    similarity: float
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChunkDuplicateStatusUpdate(BaseModel):
    status: str


class PaginatedChunkDuplicateResponse(BaseModel):
    results: List[ChunkDuplicateResponse]
    total: int
