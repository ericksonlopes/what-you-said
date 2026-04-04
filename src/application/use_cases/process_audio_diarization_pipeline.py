import logging
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, cast, Optional
from urllib.parse import unquote

from sqlalchemy.orm import Session

from src.infrastructure.repositories.sql.diarization_repository import (
    DiarizationRepository,
)
from src.config.settings import settings

from src.infrastructure.repositories.storage.storage import StorageService
from src.infrastructure.services.whisperx_audio_diarizer import AudioDiarizer
from src.infrastructure.services.pyannote_voice_recognizer import VoiceRecognizer
from src.infrastructure.services.voice_profile_service import VoiceDB

from src.domain.interfaces.services.i_event_bus import IEventBus

from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor
from src.domain.entities.enums.diarization_status_enum import (
    DiarizationStatus,
    DiarizationStep,
)

logger = logging.getLogger(__name__)


class ProcessAudioDiarizationPipelineUseCase:
    def __init__(self, db: Session, event_bus: IEventBus | None = None):
        self.db = db
        self.repo = DiarizationRepository(db)
        self.event_bus = event_bus
        logger.info("Connecting to storage (MinIO)...")
        self.storage = StorageService()
        logger.info("Storage connection established, bucket=%s", self.storage.bucket)

    def _notify(
        self, diarization_id: str | None, status: str, message: str | None = None
    ):
        if diarization_id:
            self.repo.update_status(
                diarization_id, status, status_message=message or ""
            )
        if self.event_bus and diarization_id:
            self.event_bus.publish(
                "ingestion_status",
                {
                    "type": "diarization",
                    "id": diarization_id,
                    "status": status,
                    "message": message or f"Diarization {status}",
                },
            )

    @staticmethod
    def _sanitize_folder_name(name: str) -> str:
        name = name.lower()
        name = re.sub(r'[<>:"/\\|?*]', "", name)
        name = name.replace(" ", "_")
        name = name.strip(". _")
        return name[:100] if name else "untitled_video"

    def _extract_video_id(self, url: str) -> str | None:
        patterns = [
            r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
            r"(?:embed\/)([0-9A-Za-z_-]{11})",
            r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

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
        diarization_id: str | None = None,
    ) -> dict:
        hf_token = settings.auth.hf_token or ""
        process_id = str(uuid.uuid4())
        logger.info("[Step 0] process_id: %s", process_id)

        if diarization_id:
            self._notify(
                diarization_id,
                DiarizationStatus.PROCESSING.value,
                DiarizationStep.STARTING.value,
            )

        audio_path, video_folder = (
            None,
            os.path.join(settings.audio.output_base, process_id),
        )

        try:
            # 1. Resolve audio and metadata
            audio_path, external_source, yt_metadata = self._resolve_audio_source(
                source_type, source, language, process_id, diarization_id
            )

            # 2. Prepare folders and move audio
            clean_title = self._sanitize_folder_name(Path(audio_path).stem)
            recognition_folder = os.path.join(video_folder, "recognition")
            audio_path = self._prepare_local_workspace(
                audio_path, video_folder, process_id
            )

            # 3. Diarization
            diarizer = AudioDiarizer(
                hf_token=hf_token, model_size=model_size or "large-v2"
            )
            diarization_result = self._run_diarization(
                diarizer,
                audio_path,
                language,
                num_speakers,
                min_speakers,
                max_speakers,
                diarization_id,
            )

            # 4. Export samples and Persist to DB
            self._notify(
                diarization_id,
                DiarizationStatus.PROCESSING.value,
                DiarizationStep.EXPORTING.value,
            )
            diarization_result.export_speaker_audio(output_dir=recognition_folder)
            db_record = self.repo.save(
                result=diarization_result,
                title=clean_title,
                source_type=source_type,
                external_source=external_source,
                folder=video_folder,
                storage_path=None,
                diarization_id=diarization_id,
            )
            diarization_id = cast(str, db_record.id)

            # 5. Upload & Recognition
            storage_prefix = f"processed/{diarization_id}/recognition"
            self.storage.upload_directory(recognition_folder, storage_prefix)

            self._update_record_metadata(db_record, storage_prefix, yt_metadata)

            recognition_data = {}
            if recognize_voices:
                recognition_data = self._identify_voices(
                    recognition_folder, hf_token, diarization_id
                )
                if recognition_data:
                    db_record.recognition_results = cast(Any, recognition_data)
                    self.db.commit()

            # 6. Finalize
            self._notify(
                diarization_id,
                DiarizationStatus.COMPLETED.value,
                f"Diarização de {clean_title} concluída!",
            )
            # Clear status_message for completed jobs
            self.repo.update_status(
                diarization_id, DiarizationStatus.COMPLETED.value, status_message=""
            )

            return {
                "title": clean_title,
                "storage_path": storage_prefix,
                "diarization_result": diarization_result,
                "recognition": recognition_data,
            }

        finally:
            self._cleanup_local_files(video_folder, audio_path)

    def _resolve_audio_source(
        self,
        source_type: str,
        source: str,
        language: str | None,
        process_id: str,
        diarization_id: str | None,
    ) -> tuple[str, str, Optional[Any]]:
        if diarization_id:
            self._notify(
                diarization_id,
                DiarizationStatus.PROCESSING.value,
                DiarizationStep.DOWNLOADING.value,
            )

        yt_metadata = None
        if source_type == "youtube":
            video_id = self._extract_video_id(source)
            yt_extractor = YoutubeExtractor(
                video_id=video_id, language=language or "pt"
            )
            audio_path = yt_extractor.download_audio(
                source, output_dir=settings.audio.temp_download_dir
            )
            if not audio_path:
                raise RuntimeError("YouTube download failed")

            try:
                yt_metadata = yt_extractor.extract_metadata()
            except Exception as e:
                logger.warning("Failed to extract YouTube metadata: %s", e)
            return audio_path, source, yt_metadata

        if source_type == "upload":
            s3_key = unquote(source.replace(f"s3://{self.storage.bucket}/", ""))
            local_path = os.path.join(
                settings.audio.temp_download_dir, f"{process_id}_{Path(s3_key).name}"
            )
            os.makedirs(settings.audio.temp_download_dir, exist_ok=True)
            self.storage.download_file(s3_key, local_path)
            return local_path, source, None

        raise ValueError(f"Unsupported source type: {source_type}")

    def _prepare_local_workspace(
        self, audio_path: str, video_folder: str, process_id: str
    ) -> str:
        download_folder = os.path.join(video_folder, "download")
        os.makedirs(download_folder, exist_ok=True)
        audio_dest = os.path.join(
            download_folder, f"input_{process_id}{Path(audio_path).suffix}"
        )
        os.replace(audio_path, audio_dest)
        return audio_dest

    def _run_diarization(
        self,
        diarizer: AudioDiarizer,
        audio_path: str,
        lang: str | None,
        num: int | None,
        min_s: int | None,
        max_s: int | None,
        d_id: str | None,
    ) -> Any:
        if d_id:
            self._notify(
                d_id,
                DiarizationStatus.PROCESSING.value,
                DiarizationStep.DIARIZING.value,
            )
        return diarizer.run(
            audio_path,
            language=lang,
            num_speakers=num,
            min_speakers=min_s,
            max_speakers=max_s,
        )

    def _identify_voices(
        self, recognition_folder: str, hf_token: str, d_id: str | None
    ) -> dict:
        self._notify(
            d_id, DiarizationStatus.PROCESSING.value, DiarizationStep.RECOGNIZING.value
        )
        voice_db = VoiceDB(db=self.db, hf_token=hf_token)
        if len(voice_db) == 0:
            return {}

        recognizer = VoiceRecognizer(voice_db, hf_token=hf_token)
        batch = recognizer.identify_dir(recognition_folder)
        return {
            "mapping": batch.mapping,
            "id_mapping": batch.id_mapping,
            "details": {
                spk: {
                    "identified": r.best_match,
                    "voice_id": r.best_match_id,
                    "score": r.best_score,
                }
                for spk, r in batch.results.items()
            },
        }

    def _update_record_metadata(
        self, record: Any, storage_prefix: str, yt_metadata: Optional[Any]
    ):
        record.storage_path = cast(Any, storage_prefix)
        if yt_metadata:
            metadata_dict = (
                yt_metadata.model_dump()
                if hasattr(yt_metadata, "model_dump")
                else vars(yt_metadata)
            )
            record.source_metadata = cast(Any, metadata_dict)
        self.db.commit()

    def _cleanup_local_files(self, video_folder: str, audio_path: str | None):
        for path in [video_folder, audio_path]:
            if path and os.path.exists(path):
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                except Exception as e:
                    logger.warning("Failed cleanup for %s: %s", path, e)
