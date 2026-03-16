from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from src.domain.entities.enums.ingestion_job_status_enum import IngestionJobStatus


class IngestionJobEntity(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    content_source_id: Optional[UUID] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    status: IngestionJobStatus = Field(default=IngestionJobStatus.STARTED)
    error_message: Optional[str] = None
    status_message: Optional[str] = None
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    ingestion_type: Optional[str] = None
    chunks_count: Optional[int] = None
    embedding_model: Optional[str] = None
    pipeline_version: Optional[str] = None
