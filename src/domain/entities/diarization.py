import os
from datetime import datetime, timezone
from uuid import uuid4, UUID

import soundfile as sf
from pydantic import BaseModel, Field


class Segment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    speaker: str
    start: float
    end: float
    text: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 3)

    def to_dict(self) -> dict:
        return {
            "speaker": self.speaker,
            "start": self.start,
            "end": self.end,
            "duration": self.duration,
            "text": self.text,
        }

    @classmethod
    def create(cls, speaker: str, start: float, end: float, text: str) -> "Segment":
        return cls(speaker=speaker, start=start, end=end, text=text)

    model_config = {"from_attributes": True}


class DiarizationResult(BaseModel):
    segments: list[Segment] = Field(default_factory=list)
    language: str = "unknown"
    audio_path: str = ""

    @property
    def duration(self) -> float:
        if not self.segments:
            return 0.0
        return max(s.end for s in self.segments)

    @property
    def speakers(self) -> list[str]:
        return sorted({s.speaker for s in self.segments})

    def export_speaker_audio(self, output_dir: str) -> dict[str, str]:
        """Export individual audio files per speaker from the diarized audio."""
        os.makedirs(output_dir, exist_ok=True)
        exported: dict[str, str] = {}

        data, sr = sf.read(self.audio_path, dtype="float32")
        for speaker in self.speakers:
            speaker_segments = [s for s in self.segments if s.speaker == speaker]
            if not speaker_segments:
                continue

            import numpy as np

            chunks = []
            for seg in speaker_segments:
                start_sample = int(seg.start * sr)
                end_sample = int(seg.end * sr)
                chunks.append(data[start_sample:end_sample])

            audio_data = np.concatenate(chunks)
            output_path = os.path.join(output_dir, f"{speaker}.wav")
            sf.write(output_path, audio_data, sr)
            exported[speaker] = output_path

        return exported

    model_config = {"from_attributes": True}
