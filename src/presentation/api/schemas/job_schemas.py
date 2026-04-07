from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobResponse(BaseModel):
    id: UUID
    status: str
    current_step: Optional[int] = 0
    total_steps: Optional[int] = 0
    status_message: Optional[str] = None
    error_message: Optional[str] = None
    ingestion_type: Optional[str] = None
    source_title: Optional[str] = None
    content_source_id: Optional[UUID] = None
    subject_id: Optional[UUID] = None
    chunks_count: Optional[int] = None
    external_source: Optional[str] = None
    created_at: datetime
    finished_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedJobsResponse(BaseModel):
    items: List[JobResponse]
    total: int
    page: int
    page_size: int
    stats: Optional[dict] = None
