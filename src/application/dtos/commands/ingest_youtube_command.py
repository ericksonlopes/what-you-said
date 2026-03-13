from dataclasses import dataclass
from typing import Optional, List

from src.application.dtos.enums.youtube_data_type import YoutubeDataType


@dataclass
class IngestYoutubeCommand:
    video_url: Optional[str] = None
    video_urls: Optional[List[str]] = None

    title: Optional[str] = None

    # Subject can be provided by id or name
    subject_id: Optional[str] = None
    subject_name: Optional[str] = None

    # Type of YouTube data (video, playlist)
    data_type: YoutubeDataType = YoutubeDataType.VIDEO

    # When ingesting a video, include the full transcript as a document
    send_transcript: bool = True

    language: str = "pt"
    tokens_per_chunk: int = 512
    tokens_overlap: int = 30
    embedding_model: Optional[str] = None
