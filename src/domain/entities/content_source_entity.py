from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ContentSourceEntity(BaseModel):
    """Domain entity representing a content source (e.g., a YouTube video or document)."""

    id: UUID = Field(
        default_factory=lambda: uuid4(), description="Logical ID of the content source"
    )
    subject_id: Optional[UUID] = Field(
        default=None, description="Associated knowledge subject id"
    )
    source_type: str = Field(..., description="Type of source, e.g., 'youtube', 'pdf'")
    external_source: str = Field(..., description="External id or URL of the source")
    title: Optional[str] = Field(default=None)
    language: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ingested_at: Optional[datetime] = Field(default=None)
    processing_status: str = Field(default="processing")
    embedding_model: Optional[str] = Field(default=None)
    dimensions: Optional[int] = Field(default=None)
    total_tokens: Optional[int] = Field(default=None)
    max_tokens_per_chunk: Optional[int] = Field(default=None)
    status: str = Field(default="active")
    chunks: int = Field(default=0)
    source_metadata: Optional[dict] = Field(
        default=None, description="Source-specific metadata in JSON format"
    )
