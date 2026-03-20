from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel

from src.application.dtos.enums.youtube_data_type import YoutubeDataType


class YoutubeIngestRequest(BaseModel):
    video_url: Optional[str] = None
    video_urls: Optional[List[str]] = None
    subject_id: Optional[str] = None
    subject_name: Optional[str] = None
    title: Optional[str] = None
    language: str = "pt"
    tokens_per_chunk: int = 512
    tokens_overlap: int = 50
    data_type: YoutubeDataType = YoutubeDataType.VIDEO
    ingestion_job_id: Optional[str] = None
    reprocess: bool = False


class IngestResponse(BaseModel):
    skipped: bool = False
    reason: Optional[str] = None
    source_id: Optional[UUID] = None
    job_id: Optional[UUID] = None
    created_chunks: Optional[int] = None
    vector_ids: List[str] = []
    video_results: List[Dict] = []
