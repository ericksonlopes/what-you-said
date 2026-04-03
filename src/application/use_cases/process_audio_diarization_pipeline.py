import logging
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote

from sqlalchemy.orm import Session

from src.config.settings import settings
from src.infrastructure.services.youtube_audio_downloader import AudioDownloader
from src.infrastructure.repositories.sql.repositories import DiarizationRepository
from src.infrastructure.repositories.storage.storage import StorageService
from src.infrastructure.services.whisperx_audio_diarizer import AudioDiarizer
from src.infrastructure.services.pyannote_voice_recognizer import VoiceRecognizer
from src.infrastructure.services.voice_profile_service import VoiceDB

logger = logging.getLogger(__name__)


class ProcessAudioDiarizationPipelineUseCase:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DiarizationRepository(db)
        logger.info("Connecting to storage (MinIO)...")
        self.storage = StorageService()
        logger.info("Storage connection established, bucket=%s", self.storage.bucket)

    @staticmethod
    def _sanitize_folder_name(name: str) -> str:
        name = name.lower()
        name = re.sub(r'[<>:"/\\|?*]', "", name)
        name = name.replace(" ", "_")
        name = name.strip(". _")
        return name[:100] if name else "untitled_video"

    def execute(
        self,
        source_type: str,
        source: str,
        language: str | None = "pt",
        num_speakers: int | None = None,
        min_speakers: int | None = None,
        max_speakers: int | None = None,
        model_size: str | None = "large-v2",
        recognize_voices: bool | None = True,
    ) -> dict:
        audio_cfg = settings.audio
        hf_token = settings.auth.hf_token or ""
        # Generate a unique ID for this processing run to avoid path issues
        process_id = str(uuid.uuid4())
        logger.info(
            "[Step 0] HF token present: %s, process_id: %s", bool(hf_token), process_id
        )

        # 1. Resolve audio source
        logger.info(
            "[Step 1] Resolving audio source: type=%s, source=%s", source_type, source
        )
        if source_type == "youtube":
            downloader = AudioDownloader(output_dir=audio_cfg.temp_download_dir)
            logger.info("[Step 1] Downloading from YouTube...")
            audio_path = downloader.download(source)
            if not audio_path:
                raise RuntimeError("YouTube download failed")
            logger.info("[Step 1] Download complete: %s", audio_path)
            external_source = source
        elif source_type == "upload":
            # Clean possible s3:// prefix
            s3_key = unquote(source.replace(f"s3://{self.storage.bucket}/", ""))
            local_path = os.path.join(
                audio_cfg.temp_download_dir, f"{process_id}_{Path(s3_key).name}"
            )
            os.makedirs(audio_cfg.temp_download_dir, exist_ok=True)
            logger.info(
                "[Step 1] Downloading from S3: key=%s -> %s", s3_key, local_path
            )
            self.storage.download_file(s3_key, local_path)
            audio_path = local_path
            external_source = source
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

        clean_title = self._sanitize_folder_name(Path(audio_path).stem)
        # Use process_id for the folder name instead of clean_title to avoid Windows path issues
        video_folder = os.path.join(audio_cfg.output_base, process_id)
        download_folder = os.path.join(video_folder, "download")
        recognition_folder = os.path.join(video_folder, "recognition")

        os.makedirs(download_folder, exist_ok=True)
        # Keep the original filename but in a safe directory
        audio_dest = os.path.join(
            download_folder, f"input_{process_id}{Path(audio_path).suffix}"
        )
        os.replace(audio_path, audio_dest)
        audio_path = audio_dest
        logger.info("[Step 1] Audio file ready at: %s", audio_path)

        # 2. Diarization
        logger.info(
            "[Step 2] Starting diarization (model=%s, language=%s)...",
            model_size,
            language,
        )
        diarizer = AudioDiarizer(hf_token=hf_token, model_size=model_size or "large-v2")
        diarization_result = diarizer.run(
            audio_path,
            language=language,
            num_speakers=num_speakers,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )
        logger.info(
            "[Step 2] Diarization complete: %d segments, %d speakers, duration=%.1fs",
            len(diarization_result.segments),
            len(diarization_result.speakers),
            diarization_result.duration,
        )

        logger.info("[Step 2] Exporting speaker audio to %s...", recognition_folder)
        diarization_result.export_speaker_audio(output_dir=recognition_folder)

        # Persist to database first (to get the UUID for storage path)
        logger.info("[Step 2] Creating diarization record in database...")
        db_record = self.repo.save(
            result=diarization_result,
            title=clean_title,
            source_type=source_type,
            external_source=external_source,
            folder=video_folder,
            storage_path=None,
        )
        diarization_id = db_record.id
        logger.info("[Step 2] Record created: id=%s", diarization_id)

        # Upload speaker audio to storage using UUID
        storage_prefix = f"processed/{diarization_id}/recognition"
        logger.info("[Step 2] Uploading speaker audio to S3: %s", storage_prefix)
        self.storage.upload_directory(recognition_folder, storage_prefix)

        # Update storage path in database (using only the relative prefix)
        db_record.storage_path = cast(Any, storage_prefix)
        self.db.commit()
        logger.info("[Step 2] Record updated with storage_path: %s", storage_prefix)

        # 3. Voice recognition
        recognition_data: dict[str, object] | None = None
        if recognize_voices:
            logger.info("[Step 3] Starting voice recognition...")
            voice_db = VoiceDB(db=self.db, hf_token=hf_token)
            voice_count = len(voice_db)
            logger.info("[Step 3] Voice DB has %d profiles", voice_count)
            if voice_count > 0:
                recognizer = VoiceRecognizer(voice_db, hf_token=hf_token)
                batch = recognizer.identify_dir(recognition_folder)
                recognition_data = {
                    "mapping": batch.mapping,
                    "details": {
                        spk: {"identified": r.best_match, "score": r.best_score}
                        for spk, r in batch.results.items()
                    },
                }
                db_record.recognition_results = cast(Any, recognition_data)
                self.db.commit()
                logger.info(
                    "[Step 3] Recognition complete: %s", recognition_data["mapping"]
                )
            else:
                logger.info("[Step 3] Skipped recognition (no voice profiles)")
        else:
            logger.info("[Step 3] Recognition disabled by request")

        # Cleanup local files
        try:
            shutil.rmtree(video_folder)
            logger.info("Cleaned up local folder: %s", video_folder)
        except Exception as e:
            logger.warning("Failed to cleanup local folder %s: %s", video_folder, e)

        logger.info("Pipeline complete for title=%s", clean_title)
        return {
            "title": clean_title,
            "storage_path": storage_prefix,
            "diarization_result": diarization_result,
            "recognition": recognition_data,
        }
