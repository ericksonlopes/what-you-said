from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID


@dataclass
class IngestDiarizationCommand:
    diarization_id: UUID
    subject_id: UUID
    subject_name: Optional[str] = None
    name: Optional[str] = None
    language: str = "pt"
    tokens_per_chunk: int = 512
    tokens_overlap: int = 50
    ingestion_job_id: Optional[UUID] = None
    reprocess: bool = False
    source_type: Optional[str] = None
    external_source: Optional[str] = None
    source_metadata: Optional[Dict[str, Any]] = None
