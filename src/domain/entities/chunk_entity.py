from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.domain.entities.source_type_enum_entity import SourceType


class ChunkEntity(BaseModel):
    """Domain entity representing a content chunk.

    Kept intentionally lightweight. job_id and content_source_id are optional in the
    domain models; persistence will ensure required identifiers when needed.
    """

    id: UUID = Field(default_factory=lambda: uuid4(), description="Logical ID of the chunk")
    job_id: Optional[UUID] = Field(default=None, description="ID of the processing job that created this chunk")
    content_source_id: Optional[UUID] = Field(default=None,
                                              description="ID of the original content source, e.g., video id or document id")
    source_type: SourceType = Field(description="e.g., YOUTUBE, PDF, WEB_PAGE")
    external_source: Optional[str] = Field(default=None)
    subject_id: Optional[UUID] = Field(default=None)

    content: Optional[str] = Field(default=None)
    extra: Dict[str, Any] = Field(default_factory=dict)

    language: Optional[str] = Field(default=None)
    embedding_model: Optional[str] = Field(default=None)

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version_number: int = Field(default=1)

