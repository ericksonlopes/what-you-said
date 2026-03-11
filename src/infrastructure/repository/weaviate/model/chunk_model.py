from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ChunkModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4(), description="Logical ID of the chunk within the source")

    job_id: UUID = Field(description="ID of the processing job that created this chunk")
    content_source_id: UUID = Field(description="ID of the original content source, e.g., video ID, document ID, etc.")
    source_type: str = Field(description="e.g., YOUTUBE, PDF, WEB_PAGE, etc.")
    external_source: Optional[str] = Field(description="URL, file path, id, etc.")
    subject_id: Optional[UUID] = Field(description="Optional subject or category for the chunk")

    content: Optional[str] = Field(description="Text content of the chunk")
    extra: Dict[str, Any] = Field(default_factory=dict)

    language: Optional[str] = Field(default=None, description="Language of the content, e.g., 'en', 'pt', etc.")
    embedding_model: Optional[str] = Field(description="Name of the embedding model used to generate the vector")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version_number: int = 1
