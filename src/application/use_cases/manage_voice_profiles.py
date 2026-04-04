import os

from sqlalchemy.orm import Session

from src.config.settings import settings
from src.infrastructure.repositories.sql.diarization_repository import DiarizationRepository
from src.infrastructure.repositories.storage.storage import StorageService
from src.infrastructure.services.voice_profile_service import VoiceDB


class RegisterNewVoiceProfileUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, name: str, audio_path: str, force: bool | None = False) -> str:
        hf_token = settings.auth.hf_token or ""
        voice_db = VoiceDB(db=self.db, hf_token=hf_token)
        return voice_db.add(name=name, audio_path=audio_path, force=force)


class ListRegisteredVoiceProfilesUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self) -> list[dict]:
        from src.infrastructure.repositories.sql.models.voice_record import VoiceRecord
        records = self.db.query(VoiceRecord).all()
        return [
            {
                "id": r.id,
                "name": r.name,
                "audio_source": r.audio_source,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in records
        ]


class DeleteVoiceProfileUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(self, name: str) -> None:
        hf_token = settings.auth.hf_token or ""
        voice_db = VoiceDB(db=self.db, hf_token=hf_token)
        voice_db.remove(name)


class TrainVoiceProfileFromSpeakerSegmentUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DiarizationRepository(db)
        self.storage = StorageService()

    def execute(
        self,
        diarization_id: str,
        speaker_label: str,
        name: str,
        force: bool | None = False,
    ) -> str:
        record = self.repo.get_by_id(diarization_id)
        if not record:
            raise ValueError(f"Diarization not found: {diarization_id}")

        if not record.storage_path:
            raise ValueError("No storage path found for this diarization.")

        s3_key = f"{record.storage_path}/{speaker_label}.wav"

        # Download speaker audio to temp
        audio_cfg = settings.audio
        local_path = os.path.join(
            audio_cfg.temp_download_dir, f"train_{diarization_id}_{speaker_label}.wav"
        )
        os.makedirs(audio_cfg.temp_download_dir, exist_ok=True)

        try:
            self.storage.download_file(s3_key, local_path)
        except Exception:
            raise ValueError(f"Speaker audio not found in storage: {speaker_label}")

        try:
            hf_token = settings.auth.hf_token or ""
            voice_db = VoiceDB(db=self.db, hf_token=hf_token)
            return voice_db.add(name=name, audio_path=local_path, force=force)
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)
