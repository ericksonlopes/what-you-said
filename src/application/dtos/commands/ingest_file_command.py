from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class IngestFileCommand:
    file_name: str
    file_path: Optional[str] = None
    file_url: Optional[str] = None

    # Subject can be provided by id or name
    subject_id: Optional[UUID] = None
    subject_name: Optional[str] = None

    title: Optional[str] = None
    language: str = "pt"

    # Processing parameters
    tokens_per_chunk: int = 512
    tokens_overlap: int = 50

    embedding_model: Optional[str] = None
    reprocess: bool = False
    do_ocr: bool = False

    # Optional pre-created job id
    ingestion_job_id: Optional[UUID] = None

    # Origin info (e.g. from YouTube diarization)
    source_type: Optional[str] = None
    external_source: Optional[str] = None
    source_metadata: Optional[dict] = None

    # Cleanup logic
    delete_after_ingestion: bool = False
