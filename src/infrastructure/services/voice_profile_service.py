import logging
import os
import uuid
from typing import cast
from urllib.parse import unquote

import numpy as np
from sqlalchemy.orm import Session

from src.config.settings import settings
from src.infrastructure.repositories.sql.models.voice_record import VoiceRecord
from src.infrastructure.repositories.storage.storage import StorageService
from src.infrastructure.utils.audio_utils import get_best_device

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
            from pyannote.audio import Model, Inference
            import torch

            model = Model.from_pretrained(
                "pyannote/wespeaker-voxceleb-resnet34-LM", use_auth_token=self.hf_token
            )
            device = torch.device(self._device)
            self._inference = Inference(model, window="whole", device=device)
        return self._inference

    def _extract_embedding(self, audio_path: str) -> list[float]:
        from src.infrastructure.utils.audio_utils import load_audio_tensor

        inference = self._get_inference()
        # Pass loaded audio tensor instead of file path to bypass pyannote internal AudioDecoder issues
        audio_dict = load_audio_tensor(audio_path)
        embedding = inference(audio_dict)
        return embedding.tolist()

    def add(self, name: str, audio_path: str, force: bool | None = False) -> str:
        temp_download_dir = settings.audio.temp_download_dir
        local_temp_file = None

        # Check if it's an S3-like path or if local file doesn't exist
        is_s3 = (
            audio_path.startswith("s3://")
            or audio_path.startswith("processed/")
            or audio_path.startswith("voices/")
        )

        if is_s3 or not os.path.exists(audio_path):
            # Clean possible prefix and unquote
            s3_key = unquote(audio_path.replace(f"s3://{self.storage.bucket}/", ""))
            local_temp_file = os.path.join(
                temp_download_dir, f"tmp_voice_{uuid.uuid4()}.wav"
            )
            os.makedirs(temp_download_dir, exist_ok=True)

            try:
                logger.info("Downloading reference audio from S3: %s", s3_key)
                self.storage.download_file(s3_key, local_temp_file)
                audio_path = local_temp_file
            except Exception as e:
                if is_s3:
                    raise ValueError(
                        f"Failed to download from S3 (key: {s3_key}): {str(e)}"
                    )
                else:
                    raise FileNotFoundError(
                        f"Local file not found and S3 download skipped: {audio_path}"
                    )

        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Final audio path does not exist: {audio_path}")

        try:
            existing = (
                self.db.query(VoiceRecord).filter(VoiceRecord.name == name).first()
            )

            logger.info("Extracting embedding for voice: %s", name)
            new_embedding = np.array(self._extract_embedding(audio_path))
            voice_id = str(uuid.uuid4())

            if existing:
                logger.info("Reinforcing existing voice profile: %s", name)
                # Combine embeddings (simple average)
                old_emb = np.array(existing.embedding)
                combined_emb = (old_emb + new_embedding) / 2.0
                existing.embedding = combined_emb.tolist()

                # Store additional audio sample in the voice's UUID folder
                target_s3_key = f"voices/{existing.id}/sample_{voice_id}.wav"
                self.storage.upload_file(audio_path, target_s3_key)

                self.db.commit()
                return str(existing.id)

            # Create new voice if doesn't exist
            # Use voice_id (UUID) as the folder name
            target_s3_key = f"voices/{voice_id}/reference_{voice_id}.wav"
            logger.info("Uploading reference audio to: %s", target_s3_key)
            s3_url_key = self.storage.upload_file(audio_path, target_s3_key)

            new_voice = VoiceRecord(
                id=voice_id,
                name=name,
                embedding=new_embedding.tolist(),
                audio_source=s3_url_key,
            )
            self.db.add(new_voice)
            self.db.commit()
            return voice_id

        finally:
            if local_temp_file and os.path.exists(local_temp_file):
                os.remove(local_temp_file)

    def remove(self, name: str) -> None:
        voice = self.db.query(VoiceRecord).filter(VoiceRecord.name == name).first()
        if not voice:
            raise KeyError(f"'{name}' not found.")

        s3_key = voice.audio_source.replace(f"s3://{self.storage.bucket}/", "")
        try:
            self.storage.delete_file(s3_key)
        except Exception:
            pass

        self.db.delete(voice)
        self.db.commit()

    def list_voices(self) -> dict[str, str]:
        voices = self.db.query(VoiceRecord).all()
        return {cast(str, v.name): cast(str, v.audio_source) for v in voices}

    @property
    def voices(self) -> dict:
        records = self.db.query(VoiceRecord).all()
        return {
            cast(str, r.name): {"embedding": r.embedding, "id": cast(str, r.id)}
            for r in records
        }

    def __len__(self) -> int:
        return self.db.query(VoiceRecord).count()
