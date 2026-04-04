from enum import Enum
from typing import Optional

from pydantic import BaseModel


class AudioSourceType(str, Enum):
    YOUTUBE = "youtube"
    UPLOAD = "upload"


class AudioProcessingRequest(BaseModel):
    source_type: AudioSourceType
    source: str
    language: Optional[str] = "pt"
    num_speakers: Optional[int] = None
    min_speakers: Optional[int] = None
    max_speakers: Optional[int] = None
    model_size: Optional[str] = "base"
    recognize_voices: Optional[bool] = True


class UpdateDiarizationRequest(BaseModel):
    segments: list[dict]
