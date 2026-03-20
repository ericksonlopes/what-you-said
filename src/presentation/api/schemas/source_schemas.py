from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class SourceResponse(BaseModel):
    id: UUID
    title: Optional[str] = None
    status: Optional[str] = "active"
    processing_status: Optional[str] = "pending"
    source_type: str
    subject_id: UUID
    external_source: Optional[str] = None
    embedding_model: Optional[str] = None
    dimensions: Optional[int] = None
    total_tokens: Optional[int] = None
    max_tokens_per_chunk: Optional[int] = None
    chunks: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
