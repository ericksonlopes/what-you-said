from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class IngestFileCommand:
    file_path: str
    file_name: str

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

    # Optional pre-created job id
    ingestion_job_id: Optional[UUID] = None
