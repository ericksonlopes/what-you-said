import logging
import os
import shutil
from typing import Any, cast

from sqlalchemy.orm import Session

from src.config.settings import settings
from src.infrastructure.repositories.sql.diarization_repository import (
    DiarizationRepository,
)
from src.infrastructure.repositories.storage.storage import StorageService
from src.infrastructure.services.pyannote_voice_recognizer import VoiceRecognizer
from src.infrastructure.services.voice_profile_service import VoiceDB

logger = logging.getLogger(__name__)


class IdentifySpeakersInProcessedAudioUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DiarizationRepository(db)
        self.storage = StorageService()

    def execute(self, diarization_id: str) -> dict:
        record = self.repo.get_by_id(diarization_id)
        if not record:
            raise ValueError(f"Diarization not found: {diarization_id}")

        audio_cfg = settings.audio
        hf_token = settings.auth.hf_token or ""

        voice_db = VoiceDB(db=self.db, hf_token=hf_token)
        if len(voice_db) == 0:
            raise ValueError("Voice database is empty. Register voices first.")

        # Download speaker audio from storage to temp dir
        s3_prefix = cast(str, record.storage_path)
        if not s3_prefix:
            raise ValueError("No storage path found for this diarization.")

        local_dir = os.path.join(audio_cfg.temp_download_dir, f"recognize_{diarization_id}")
        os.makedirs(local_dir, exist_ok=True)

        try:
            self.storage.download_directory(s3_prefix, local_dir)

            recognizer = VoiceRecognizer(voice_db, hf_token=hf_token)
            batch = recognizer.identify_dir(local_dir)

            mapping = batch.mapping
            id_mapping = batch.id_mapping

            # Automatic reinforcement: add matched segments to voice profile
            reinforced_paths = {}
            for spk, match in batch.results.items():
                best_match = match.best_match
                if best_match:
                    try:
                        logger.info(
                            "Auto-reinforcing voice profile '%s' with segment '%s'",
                            best_match,
                            spk,
                        )
                        _, s3_path = voice_db.add(name=best_match, audio_path=match.audio_path)
                        if s3_path:
                            reinforced_paths[spk] = s3_path
                    except Exception as e:
                        logger.error("Failed to reinforce voice profile '%s': %s", best_match, e)

            recognition_data: dict[str, object] = {
                "mapping": mapping,
                "id_mapping": id_mapping,
                "details": {
                    spk: {
                        "identified": r.best_match,
                        "voice_id": r.best_match_id,
                        "score": r.best_score,
                        "reinforced_sample_path": reinforced_paths.get(spk),
                    }
                    for spk, r in batch.results.items()
                },
            }

            record.recognition_results = cast(Any, recognition_data)
            self.db.commit()

            return recognition_data
        finally:
            try:
                shutil.rmtree(local_dir)
            except Exception as e:
                logger.warning("Failed to cleanup local directory %s: %s", local_dir, e)
