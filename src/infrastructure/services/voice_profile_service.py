import datetime
import logging
import os
import uuid
from contextlib import suppress
from typing import Any, cast
from urllib.parse import unquote

import numpy as np
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.infrastructure.repositories.sql.models.voice_record import VoiceRecord
from src.infrastructure.repositories.storage.storage import StorageService
from src.infrastructure.utils.audio_utils import cosine_similarity, get_best_device

logger = logging.getLogger(__name__)


class VoiceDB:
    def __init__(self, db: Session, hf_token: str):
        self.db = db
        self.hf_token = hf_token
        self.storage = StorageService()
        self._device = get_best_device()
        self._inference = None

    def _get_inference(self):
        if self._inference is None:
            import torch
            from pyannote.audio import Inference, Model

            model = Model.from_pretrained("pyannote/wespeaker-voxceleb-resnet34-LM", use_auth_token=self.hf_token)
            device = torch.device(self._device)
            self._inference = Inference(model, window="whole", device=device)
        return self._inference

    def _extract_embedding(self, audio_path: str) -> list[float]:
        from src.infrastructure.utils.audio_utils import load_audio_tensor

        inference = self._get_inference()
        audio_dict = load_audio_tensor(audio_path)
        embedding = inference(audio_dict)
        return embedding.tolist()

    def add(self, name: str, audio_path: str) -> tuple[str, str]:
        if not name or not name.strip():
            raise ValueError("Name required")

        temp_download_dir = settings.audio.temp_download_dir
        local_temp_file = None

        is_s3 = (
            audio_path.startswith("s3://") or audio_path.startswith("processed/") or audio_path.startswith("voices/")
        )

        if is_s3 or not os.path.exists(audio_path):
            s3_key = unquote(audio_path.replace(f"s3://{self.storage.bucket}/", ""))
            local_temp_file = os.path.join(temp_download_dir, f"tmp_voice_{uuid.uuid4()}.wav")
            os.makedirs(temp_download_dir, exist_ok=True)

            try:
                logger.info("Downloading reference audio from S3: %s", s3_key)
                self.storage.download_file(s3_key, local_temp_file)
                audio_path = local_temp_file
            except Exception as e:
                if is_s3:
                    raise ValueError(f"Failed to download from S3 (key: {s3_key}): {str(e)}")
                else:
                    raise FileNotFoundError(f"Local file not found and S3 download skipped: {audio_path}")

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Final audio path does not exist: {audio_path}")

        record: VoiceRecord | None = None
        try:
            existing = self.db.query(VoiceRecord).filter(VoiceRecord.name == name).first()
            is_reinforcement = existing is not None

            # Create or mark the target row as "processing" and commit BEFORE the
            # slow embedding extraction, so the API/UI can observe the in-flight
            # state while training/reinforcement runs.
            if is_reinforcement and existing:
                record = existing
                record.status = cast(Any, "processing")
                record.status_message = cast(Any, f"Reforçando voz '{name}'...")
            else:
                voice_id = str(uuid.uuid4())
                record = VoiceRecord(
                    id=voice_id,
                    name=name,
                    embedding=[],
                    audios_path=f"voices/{voice_id}/",
                    status="processing",
                    status_message=f"Treinando voz '{name}'...",
                    created_at=datetime.datetime.now(datetime.UTC),
                )
                self.db.add(record)
            self.db.commit()

            if not record:
                raise ValueError("Failed to create or retrieve voice record.")

            logger.info("Extracting embedding for voice: %s", name)
            new_embedding = np.array(self._extract_embedding(audio_path))

            if is_reinforcement:
                old_emb = np.array(record.embedding)
                similarity = cosine_similarity(old_emb, new_embedding)

                if similarity >= 0.95:
                    logger.info(
                        "Skipping reinforcement for '%s': audio too similar "
                        "(similarity=%.4f), would duplicate existing reference.",
                        name,
                        similarity,
                    )
                    record.status = cast(Any, "ready")
                    record.status_message = cast(Any, None)
                    self.db.commit()
                    return str(record.id), ""

                logger.info(
                    "Reinforcing existing voice profile: %s (similarity=%.4f)",
                    name,
                    similarity,
                )
                combined_emb = (old_emb + new_embedding) / 2.0
                record.embedding = combined_emb.tolist()

                sample_id = str(uuid.uuid4())
                target_s3_key = f"{record.audios_path}sample_{sample_id}.wav"
                self.storage.upload_file(audio_path, target_s3_key)
            else:
                record.embedding = new_embedding.tolist()
                target_s3_key = f"{record.audios_path}reference_{record.id}.wav"
                logger.info("Uploading reference audio to: %s", target_s3_key)
                self.storage.upload_file(audio_path, target_s3_key)

            record.status = cast(Any, "ready")
            record.status_message = cast(Any, None)
            self.db.commit()
            return str(record.id), target_s3_key

        except Exception as e:
            if record is not None:
                with suppress(Exception):
                    self.db.rollback()
                    # Re-fetch to work on an attached instance after rollback
                    fresh = self.db.query(VoiceRecord).filter(VoiceRecord.id == record.id).first()
                    if fresh is not None:
                        fresh.status = cast(Any, "failed")
                        fresh.status_message = cast(Any, str(e)[:500])
                        self.db.commit()
            raise
        finally:
            if local_temp_file and os.path.exists(local_temp_file):
                os.remove(local_temp_file)

    def remove(self, name: str) -> None:
        voice = self.db.query(VoiceRecord).filter(VoiceRecord.name == name).first()
        if not voice:
            raise KeyError(f"'{name}' not found.")

        # Delete all files under the voice's S3 directory
        if voice.audios_path:
            files = self.storage.list_files(prefix=cast(str, voice.audios_path))
            for f in files:
                with suppress(Exception):
                    self.storage.delete_file(f["key"])

        self.db.delete(voice)
        self.db.commit()

    def list_audio_files(self, voice_id: str) -> list[dict]:
        """List audio files from S3 for a given voice profile."""
        voice = self.db.query(VoiceRecord).filter(VoiceRecord.id == voice_id).first()
        if not voice or not voice.audios_path:
            return []
        return self.storage.list_files(prefix=cast(str, voice.audios_path), extension=".wav")

    def delete_audio_file(self, s3_key: str) -> None:
        """Delete a specific audio file from S3."""
        self.storage.delete_file(s3_key)

    def list_voices(self) -> dict[str, str]:
        voices = self.db.query(VoiceRecord).filter(VoiceRecord.status == "ready").all()
        return {cast(str, v.name): cast(str, v.audios_path) for v in voices}

    @property
    def voices(self) -> dict:
        # Only expose voices that finished training — placeholder rows in
        # "processing" state have empty embeddings and would break similarity
        # comparisons.
        records = self.db.query(VoiceRecord).filter(VoiceRecord.status == "ready").all()
        return {cast(str, r.name): {"embedding": r.embedding, "id": cast(str, r.id)} for r in records}

    def __len__(self) -> int:
        return self.db.query(VoiceRecord).filter(VoiceRecord.status == "ready").count()
