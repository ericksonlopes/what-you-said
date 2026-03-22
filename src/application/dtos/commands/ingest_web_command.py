from dataclasses import dataclass
from typing import Optional


@dataclass
class IngestWebCommand:
    url: str

    # Optional CSS selector to focus on specific content
    css_selector: Optional[str] = None

    # Title override (if None, extract from page)
    title: Optional[str] = None

    # Subject can be provided by id or name
    subject_id: Optional[str] = None
    subject_name: Optional[str] = None

    # Processing parameters
    language: str = "pt"
    tokens_per_chunk: int = 512
    tokens_overlap: int = 50

    # Scraping parameters
    depth: int = 1

    # Optional pre-created job id to avoid duplicates
    ingestion_job_id: Optional[str] = None
    reprocess: bool = False
