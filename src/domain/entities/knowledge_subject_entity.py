from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class KnowledgeSubjectEntity(BaseModel):
    """Domain entity representing a knowledge subject.

    This entity is used as the output DTO for service layer operations.
    """

    id: UUID = Field(
        default_factory=lambda: uuid4(),
        description="Logical ID of the knowledge subject",
    )
    external_ref: Optional[str] = Field(
        default=None, description="Optional external reference ID"
    )
    name: str = Field(..., description="Human-readable name of the subject")
    description: Optional[str] = Field(
        default=None, description="Optional longer description"
    )
    icon: Optional[str] = Field(default=None, description="Icon name for the frontend")
    source_count: int = Field(default=0, description="Number of content sources")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )
