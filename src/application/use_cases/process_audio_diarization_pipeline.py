import logging
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, Optional, cast
from urllib.parse import unquote

from sqlalchemy.orm import Session

from src.config.settings import settings
from src.domain.entities.enums.diarization_status_enum import (
    DiarizationStatus,
    DiarizationStep,
)
from src.domain.interfaces.services.i_event_bus import IEventBus
from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor
from src.infrastructure.repositories.sql.diarization_repository import (
    DiarizationRepository,
)
from src.infrastructure.repositories.storage.storage import StorageService
from src.infrastructure.services.pyannote_voice_recognizer import VoiceRecognizer
from src.infrastructure.services.voice_profile_service import VoiceDB
from src.infrastructure.services.whisperx_audio_diarizer import AudioDiarizer

logger = logging.getLogger(__name__)


class ProcessAudioDiarizationPipelineUseCase:
    REINFORCEMENT_THRESHOLD = 0.92

    def __init__(
        self,
        db: Session,
        event_bus: IEventBus | None = None,
        cs_service: Any | None = None,
    ):
        self.db = db
        self.repo = DiarizationRepository(db)
        self.event_bus = event_bus
        self.cs_service = cs_service
        logger.info("Connecting to storage (MinIO)...")
        self.storage = StorageService()
        logger.info("Storage connection established, bucket=%s", self.storage.bucket)

    def _notify(self, diarization_id: str | None, status: str, message: str | None = None):
        if diarization_id:
            self.repo.update_status(diarization_id, status, status_message=message or "")
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

        video_folder = os.path.join(settings.audio.output_base, process_id)
        audio_path = None

        try:
            # 1. Resolve audio and metadata
            audio_raw_path, external_source, yt_metadata = self._resolve_audio_source(
                source_type, source, language, process_id, diarization_id
            )

            # 2. Prepare folders and workspace
            display_name = self._resolve_display_name(audio_raw_path, yt_metadata)
            recognition_folder = os.path.join(video_folder, "recognition")
            audio_path = self._prepare_local_workspace(audio_raw_path, video_folder, process_id)

            # 3. Diarization
            diarizer = AudioDiarizer(hf_token=hf_token, model_size=model_size or "large-v2")
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
            db_record = self._persist_results(
                diarization_result,
                recognition_folder,
                display_name,
                source_type,
                external_source,
                video_folder,
                diarization_id,
            )
            diarization_id = cast(str, db_record.id)

            # 5. Upload & Recognition
            storage_prefix = f"processed/{diarization_id}/recognition"
            self.storage.upload_directory(recognition_folder, storage_prefix)
            self._update_record_metadata(db_record, storage_prefix, yt_metadata)

            recognition_data = {}
            if recognize_voices:
                recognition_data = self._identify_voices(recognition_folder, hf_token, diarization_id)
                if recognition_data:
                    db_record.recognition_results = cast(Any, recognition_data)
                    self.db.commit()

            # 6. Finalize
            self._finalize_pipeline(
                diarization_id,
                display_name,
                source_type,
                external_source,
                language,
                db_record,
            )

            return {
                "name": display_name,
                "storage_path": storage_prefix,
                "diarization_result": diarization_result,
                "recognition": recognition_data,
            }

        finally:
            self._cleanup_local_files(video_folder, audio_path)

    def _resolve_display_name(self, audio_raw_path: str, yt_metadata: Optional[Any]) -> str:
        original_title = Path(audio_raw_path).stem
        if yt_metadata and hasattr(yt_metadata, "title") and yt_metadata.title:
            return yt_metadata.title
        return original_title

    def _persist_results(
        self,
        result: Any,
        recognition_folder: str,
        display_name: str,
        source_type: str,
        external_source: str,
        video_folder: str,
        diarization_id: str | None,
    ) -> Any:
        self._notify(
            diarization_id,
            DiarizationStatus.PROCESSING.value,
            DiarizationStep.EXPORTING.value,
        )
        # Export individual speaker samples (optimized with min_duration filter in Segment entity)
        result.export_speaker_audio(output_dir=recognition_folder)

        db_record = self.repo.save(
            result=result,
            name=display_name,
            source_type=source_type,
            external_source=external_source,
            folder=video_folder,
            storage_path=None,
            diarization_id=diarization_id,
        )
        return db_record

    def _finalize_pipeline(
        self,
        diarization_id: str,
        display_name: str,
        source_type: str,
        external_source: str,
        language: str | None,
        db_record: Any,
    ):
        self._notify(
            diarization_id,
            DiarizationStatus.AWAITING_VERIFICATION.value,
            f"Diarização de {display_name} concluída!",
        )
        # Update status for the job
        self.repo.update_status(
            diarization_id,
            DiarizationStatus.AWAITING_VERIFICATION.value,
            status_message="Aguardando revisão dos falantes",
        )

        # Create/Update ContentSource in AWAITING_VERIFICATION status
        if self.cs_service:
            try:
                from src.domain.entities.enums.content_source_status_enum import (
                    ContentSourceStatus,
                )
                from src.domain.entities.enums.source_type_enum_entity import SourceType

                cs_source_type = SourceType.YOUTUBE if source_type == "youtube" else SourceType.AUDIO
                subject_id = getattr(db_record, "subject_id", None)

                # Check if source already exists to avoid duplication
                existing_source = self.cs_service.get_by_source_info(
                    source_type=cs_source_type,
                    external_source=external_source,
                    subject_id=subject_id,
                )

                source_metadata = {
                    **(cast(dict, db_record.source_metadata) or {}),
                    "diarization_id": diarization_id,
                }

                if existing_source:
                    logger.info(
                        "Found existing ContentSource %s. Updating for diarization %s",
                        existing_source.id,
                        diarization_id,
                    )
                    self.cs_service.update_processing_status(
                        content_source_id=existing_source.id,
                        status=ContentSourceStatus.AWAITING_VERIFICATION,
                        status_message="Aguardando revisão dos falantes",
                    )
                    # Merge metadata
                    self.cs_service.update_metadata(content_source_id=existing_source.id, metadata=source_metadata)
                else:
                    self.cs_service.create_source(
                        subject_id=subject_id,
                        source_type=cs_source_type,
                        external_source=external_source,
                        status=ContentSourceStatus.ACTIVE,
                        processing_status=ContentSourceStatus.AWAITING_VERIFICATION.value,
                        title=display_name,
                        language=language,
                        source_metadata=source_metadata,
                    )
                    logger.info(
                        "Created shallow ContentSource for diarization %s",
                        diarization_id,
                    )
            except Exception as e:
                logger.error("Failed to create/update ContentSource: %s", e)

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
            video_id = YoutubeExtractor.get_video_id(source)
            if not video_id:
                raise ValueError(f"Invalid YouTube source: {source}")

            yt_extractor = YoutubeExtractor(video_id=video_id, language=language or "pt")
            # Use the full URL for downloading to be safe
            download_url = f"https://www.youtube.com/watch?v={video_id}"
            audio_path = yt_extractor.download_audio(download_url, output_dir=settings.audio.temp_download_dir)
            if not audio_path:
                raise RuntimeError("YouTube download failed")

            try:
                yt_metadata = yt_extractor.extract_metadata()
            except Exception as e:
                logger.warning("Failed to extract YouTube metadata: %s", e)

            # Return normalized ID as external_source
            return audio_path, video_id, yt_metadata

        if source_type == "upload":
            s3_key = unquote(source.replace(f"s3://{self.storage.bucket}/", ""))
            local_path = os.path.join(settings.audio.temp_download_dir, f"{process_id}_{Path(s3_key).name}")
            os.makedirs(settings.audio.temp_download_dir, exist_ok=True)
            self.storage.download_file(s3_key, local_path)
            return local_path, source, None

        raise ValueError(f"Unsupported source type: {source_type}")

    def _prepare_local_workspace(self, audio_path: str, video_folder: str, process_id: str) -> str:
        download_folder = os.path.join(video_folder, "download")
        os.makedirs(download_folder, exist_ok=True)
        audio_dest = os.path.join(download_folder, f"input_{process_id}{Path(audio_path).suffix}")
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

    def _identify_voices(self, recognition_folder: str, hf_token: str, d_id: str | None) -> dict:
        self._notify(d_id, DiarizationStatus.PROCESSING.value, DiarizationStep.RECOGNIZING.value)
        voice_db = VoiceDB(db=self.db, hf_token=hf_token)
        if len(voice_db) == 0:
            return {}

        recognizer = VoiceRecognizer(voice_db, hf_token=hf_token)
        batch = recognizer.identify_dir(recognition_folder)

        # Automatic reinforcement: add matched segments to voice profile
        reinforced_paths = {}
        for spk, match in batch.results.items():
            best_match = match.best_match
            best_score = match.best_score or 0.0

            if best_match and best_score >= self.REINFORCEMENT_THRESHOLD:
                try:
                    logger.info(
                        "Auto-reinforcing voice profile '%s' with segment '%s' (score: %.4f)",
                        best_match,
                        spk,
                        best_score,
                    )
                    _, s3_path = voice_db.add(name=best_match, audio_path=match.audio_path)
                    if s3_path:
                        reinforced_paths[spk] = s3_path
                except Exception as e:
                    logger.error(
                        "Failed to reinforce voice profile '%s' in pipeline: %s",
                        best_match,
                        e,
                    )
            elif best_match:
                logger.info(
                    "Skipping reinforcement for '%s' (match: %s) - score %.4f below threshold %.2f",
                    spk,
                    best_match,
                    best_score,
                    self.REINFORCEMENT_THRESHOLD,
                )

        return {
            "mapping": batch.mapping,
            "id_mapping": batch.id_mapping,
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

    def _update_record_metadata(self, record: Any, storage_prefix: str, yt_metadata: Optional[Any]):
        record.storage_path = cast(Any, storage_prefix)
        if yt_metadata:
            metadata_dict = yt_metadata.model_dump() if hasattr(yt_metadata, "model_dump") else vars(yt_metadata)
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
