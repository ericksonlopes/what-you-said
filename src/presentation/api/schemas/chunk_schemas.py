from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class ChunkResponse(BaseModel):
    id: UUID
    content_source_id: UUID
    chunk_id: Optional[str] = None
    content: Optional[str] = None
    tokens_count: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChunkUpdate(BaseModel):
    content: str
