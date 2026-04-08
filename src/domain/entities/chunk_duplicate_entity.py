from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ChunkDuplicateEntity(BaseModel):
    """Domain entity representing a group of duplicate chunks."""

    id: UUID = Field(default_factory=uuid4)
    chunk_ids: List[UUID] = Field(default_factory=list)
    similarity: float
    content_source_id: Optional[str] = None
    status: str = "pending"  # e.g., "pending", "reviewed", "ignored"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
