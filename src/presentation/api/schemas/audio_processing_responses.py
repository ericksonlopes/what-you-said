from pydantic import BaseModel
from typing import List, Optional, Dict


class AudioSegmentSchema(BaseModel):
    """Schema para representar um segmento de fala individual na resposta."""

    speaker: str
    start: float
    end: float
    duration: float
    text: str


class AudioProcessingResponse(BaseModel):
    """Schema de resposta para o pipeline de processamento completo."""

    name: str
    folder: str
    segments: List[AudioSegmentSchema]
    recognition: Optional[Dict] = None
