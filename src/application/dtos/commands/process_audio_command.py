from dataclasses import dataclass
from typing import Optional


@dataclass
class ProcessAudioCommand:
    source_type: str
    source: str
    language: str = "pt"
    num_speakers: Optional[int] = 2
    min_speakers: Optional[int] = None
    max_speakers: Optional[int] = 2
    model_size: str = "large-v2"
    recognize_voices: bool = True
    diarization_id: Optional[str] = None
    subject_id: Optional[str] = None
