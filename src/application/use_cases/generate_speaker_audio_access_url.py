from sqlalchemy.orm import Session

from src.infrastructure.repositories.sql.diarization_repository import DiarizationRepository
from src.infrastructure.repositories.storage.storage import StorageService


class GenerateSpeakerAudioAccessUrlUseCase:
    def __init__(self, db: Session):
        self.repo = DiarizationRepository(db)
        self.storage = StorageService()

    def execute(self, diarization_id: str, speaker_label: str) -> dict:
        record = self.repo.get_by_id(diarization_id)
        if not record:
            raise ValueError(f"Diarization not found: {diarization_id}")

        if not record.storage_path:
            raise ValueError("No storage path found for this diarization.")

        # storage_path is now a relative key like 'processed/<uuid>/recognition'
        s3_key = f"{record.storage_path}/{speaker_label}.wav"

        url = self.storage.get_presigned_url(s3_key)
        return {"speaker": speaker_label, "url": url}
