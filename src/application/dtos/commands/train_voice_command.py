from dataclasses import dataclass
from typing import Optional


@dataclass
class TrainVoiceCommand:
    """Command to train a voice profile from a speaker segment in a diarization."""

    diarization_id: str
    speaker_label: str
    name: str
    job_id: Optional[str] = None
