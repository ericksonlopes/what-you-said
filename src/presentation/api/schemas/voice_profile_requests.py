from typing import Optional

from pydantic import BaseModel


class VoiceProfileRegistrationRequest(BaseModel):
    """Schema para cadastrar uma nova voz a partir de um caminho de áudio local ou S3."""

    name: str
    audio_path: str
    force: Optional[bool] = False


class VoiceProfileTrainingFromSpeakerRequest(BaseModel):
    """Schema para cadastrar uma nova voz a partir de um speaker detectado em um processamento anterior."""

    diarization_id: str
    speaker_label: str
    name: str
    force: Optional[bool] = False
