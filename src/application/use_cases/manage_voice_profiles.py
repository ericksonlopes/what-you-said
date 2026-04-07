import os
from contextlib import suppress
from typing import cast

from sqlalchemy.orm import Session

from src.config.settings import settings
from src.domain.interfaces.services.i_event_bus import IEventBus
from src.infrastructure.repositories.sql.diarization_repository import (
    DiarizationRepository,
)
from src.infrastructure.repositories.storage.storage import StorageService
from src.infrastructure.services.voice_profile_service import VoiceDB


class RegisterNewVoiceProfileUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, name: str, audio_path: str) -> str:
        if not name or not name.strip():
            raise ValueError("Name required")

        hf_token = settings.auth.hf_token or ""
        voice_db = VoiceDB(db=self.db, hf_token=hf_token)
        voice_id, _ = voice_db.add(name=name, audio_path=audio_path)
        return voice_id


class ListRegisteredVoiceProfilesUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self) -> list[dict]:
        from src.infrastructure.repositories.sql.models.voice_record import VoiceRecord

        storage = StorageService()
        records = self.db.query(VoiceRecord).all()

        result = []
        for r in records:
            samples_count = 0
            if r.audios_path:
                with suppress(Exception):
                    files = storage.list_files(prefix=cast(str, r.audios_path), extension=".wav")
                    samples_count = len(files)

            result.append(
                {
                    "id": r.id,
                    "name": r.name,
                    "audios_path": r.audios_path,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "samples_count": samples_count,
                    "status": r.status or "ready",
                    "status_message": r.status_message,
                }
            )
        return result


class ListVoiceAudioFilesUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, voice_id: str) -> list[dict]:
        hf_token = settings.auth.hf_token or ""
        voice_db = VoiceDB(db=self.db, hf_token=hf_token)
        return voice_db.list_audio_files(voice_id)


class DeleteVoiceAudioFileUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, s3_key: str) -> None:
        hf_token = settings.auth.hf_token or ""
        voice_db = VoiceDB(db=self.db, hf_token=hf_token)
        voice_db.delete_audio_file(s3_key)


class DeleteVoiceProfileUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, name: str) -> None:
        hf_token = settings.auth.hf_token or ""
        voice_db = VoiceDB(db=self.db, hf_token=hf_token)
        voice_db.remove(name)


class TrainVoiceProfileFromSpeakerSegmentUseCase:
    def __init__(self, db: Session, event_bus: IEventBus | None = None):
        self.db = db
        self.repo = DiarizationRepository(db)
        self.storage = StorageService()
        self.event_bus = event_bus

    def execute(
        self,
        diarization_id: str,
        speaker_label: str,
        name: str,
    ) -> str:
        record = self.repo.get_by_id(diarization_id)
        if not record:
            raise ValueError(f"Diarization not found: {diarization_id}")

        if not record.storage_path:
            raise ValueError("No storage path found for this diarization.")

        # Voice training is orthogonal to the diarization lifecycle — do NOT
        # mutate the diarization record's status here. Only emit voice-scoped
        # events so the UI can track progress per-speaker.
        if self.event_bus:
            self.event_bus.publish(
                "ingestion_status",
                {
                    "type": "voice",
                    "action": "train_progress",
                    "name": name,
                    "diarization_id": diarization_id,
                    "speaker_label": speaker_label,
                },
            )

        s3_key = f"{record.storage_path}/{speaker_label}.wav"

        audio_cfg = settings.audio
        local_path = os.path.join(audio_cfg.temp_download_dir, f"train_{diarization_id}_{speaker_label}.wav")
        os.makedirs(audio_cfg.temp_download_dir, exist_ok=True)

        try:
            self.storage.download_file(s3_key, local_path)

            hf_token = settings.auth.hf_token or ""
            voice_db = VoiceDB(db=self.db, hf_token=hf_token)
            voice_id, _ = voice_db.add(name=name, audio_path=local_path)

            if self.event_bus:
                self.event_bus.publish(
                    "ingestion_status",
                    {
                        "type": "voice",
                        "action": "train",
                        "name": name,
                        "diarization_id": diarization_id,
                        "speaker_label": speaker_label,
                    },
                )

            return voice_id

        except Exception as e:
            if self.event_bus:
                self.event_bus.publish(
                    "ingestion_status",
                    {
                        "type": "voice",
                        "action": "train_failed",
                        "name": name,
                        "diarization_id": diarization_id,
                        "speaker_label": speaker_label,
                        "error": str(e),
                    },
                )
            raise
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)
