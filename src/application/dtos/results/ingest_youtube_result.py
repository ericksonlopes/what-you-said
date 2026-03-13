from dataclasses import dataclass, field
from typing import Optional, List, Dict
from uuid import UUID


@dataclass
class IngestYoutubeResult:
    skipped: bool = False
    reason: Optional[str] = None
    source_id: Optional[UUID] = None
    created_chunks: Optional[int] = None
    vector_ids: List[str] = field(default_factory=list)

    # Detailed per-video results (useful when video_urls contains multiple entries)
    video_results: List[Dict] = field(default_factory=list)
