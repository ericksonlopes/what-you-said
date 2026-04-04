import logging
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote

from sqlalchemy.orm import Session

from src.infrastructure.repositories.sql.diarization_repository import DiarizationRepository
from src.config.settings import settings

from src.infrastructure.repositories.storage.storage import StorageService
from src.infrastructure.services.whisperx_audio_diarizer import AudioDiarizer
from src.infrastructure.services.pyannote_voice_recognizer import VoiceRecognizer
from src.infrastructure.services.voice_profile_service import VoiceDB

from src.domain.interfaces.services.i_event_bus import IEventBus

from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor

logger = logging.getLogger(__name__)


class ProcessAudioDiarizationPipelineUseCase:
    def __init__(self, db: Session, event_bus: IEventBus | None = None):
        self.db = db
        self.repo = DiarizationRepository(db)
        self.event_bus = event_bus
        logger.info("Connecting to storage (MinIO)...")
        self.storage = StorageService()
        logger.info("Storage connection established, bucket=%s", self.storage.bucket)

    def _notify(self, diarization_id: str | None, status: str, message: str | None = None):
        if self.event_bus and diarization_id:
            self.event_bus.publish("ingestion_status", {
                "type": "diarization",
                "id": diarization_id,
                "status": status,
                "message": message or f"Diarization {status}"
            })

    @staticmethod
    def _sanitize_folder_name(name: str) -> str:
        name = name.lower()
        name = re.sub(r'[<>:"/\\|?*]', "", name)
        name = name.replace(" ", "_")
        name = name.strip(". _")
        return name[:100] if name else "untitled_video"

    def _extract_video_id(self, url: str) -> str | None:
        import re
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:embed\/)([0-9A-Za-z_-]{11})',
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'
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
        audio_cfg = settings.audio
        hf_token = settings.auth.hf_token or ""
        # Generate a unique ID for this processing run to avoid path issues
        process_id = str(uuid.uuid4())
        logger.info(
            "[Step 0] HF token present: %s, process_id: %s", bool(hf_token), process_id
        )

        # Update status to processing if we have an existing record
        if diarization_id:
            msg = f"Iniciando processamento de {source_type}..."
            self.repo.update_status(diarization_id, "processing")
            self._notify(diarization_id, "processing", msg)

        audio_path = None
        video_folder = os.path.join(audio_cfg.output_base, process_id)
        
        try:
            # 1. Resolve audio source
            msg = "Baixando e extraindo áudio da fonte..."
            logger.info("[Step 1] %s", msg)
            yt_metadata = None
            if diarization_id:
                self.repo.update_status(diarization_id, "processing")
                self._notify(diarization_id, "processing", msg)

            if source_type == "youtube":
                video_id = self._extract_video_id(source)
                yt_extractor = YoutubeExtractor(video_id=video_id, language=language or "pt")
                
                # Download audio using consolidated extractor
                audio_path = yt_extractor.download_audio(source, output_dir=audio_cfg.temp_download_dir)
                if not audio_path:
                    raise RuntimeError("YouTube download failed")
                
                external_source = source
                
                try:
                    logger.info("[Step 1] Extracting YouTube metadata")
                    yt_metadata = yt_extractor.extract_metadata()
                except Exception as e:
                    logger.warning("Failed to extract YouTube metadata: %s", e)
            elif source_type == "upload":
                # Clean possible s3:// prefix
                s3_key = unquote(source.replace(f"s3://{self.storage.bucket}/", ""))
                local_path = os.path.join(
                    audio_cfg.temp_download_dir, f"{process_id}_{Path(s3_key).name}"
                )
                os.makedirs(audio_cfg.temp_download_dir, exist_ok=True)
                self.storage.download_file(s3_key, local_path)
                audio_path = local_path
                external_source = source
            else:
                raise ValueError(f"Unsupported source type: {source_type}")

            clean_title = self._sanitize_folder_name(Path(audio_path).stem)
            download_folder = os.path.join(video_folder, "download")
            recognition_folder = os.path.join(video_folder, "recognition")

            os.makedirs(download_folder, exist_ok=True)
            audio_dest = os.path.join(
                download_folder, f"input_{process_id}{Path(audio_path).suffix}"
            )
            os.replace(audio_path, audio_dest)
            audio_path = audio_dest

            # 2. Diarization
            msg = f"Analisando locutores (Modelo: {model_size})..."
            logger.info("[Step 2] %s", msg)
            if diarization_id:
                self.repo.update_status(diarization_id, "processing")
                self._notify(diarization_id, "processing", msg)

            diarizer = AudioDiarizer(hf_token=hf_token, model_size=model_size or "large-v2")
            diarization_result = diarizer.run(
                audio_path,
                language=language,
                num_speakers=num_speakers,
                min_speakers=min_speakers,
                max_speakers=max_speakers,
            )

            msg = "Exportando amostras de voz dos locutores..."
            logger.info("[Step 2] %s", msg)
            if diarization_id:
                self.repo.update_status(diarization_id, "processing")
                self._notify(diarization_id, "processing", msg)

            diarization_result.export_speaker_audio(output_dir=recognition_folder)

            # Persist to database (update existing or create new)
            db_record = self.repo.save(
                result=diarization_result,
                title=clean_title,
                source_type=source_type,
                external_source=external_source,
                folder=video_folder,
                storage_path=None,
                diarization_id=diarization_id,
            )
            diarization_id = db_record.id

            # Upload speaker audio to storage
            storage_prefix = f"processed/{diarization_id}/recognition"
            self.storage.upload_directory(recognition_folder, storage_prefix)

            db_record.storage_path = cast(Any, storage_prefix)
            if yt_metadata:
                metadata_dict = yt_metadata.model_dump() if hasattr(yt_metadata, 'model_dump') else vars(yt_metadata)
                db_record.source_metadata = cast(Any, metadata_dict)
            self.db.commit()

            # 3. Voice recognition
            recognition_data: dict[str, object] = {}

            if recognize_voices:
                msg = "Reconhecendo vozes conhecidas no áudio..."
                logger.info("[Step 3] %s", msg)
                self.repo.update_status(diarization_id, "processing")
                self._notify(diarization_id, "processing", msg)

                voice_db = VoiceDB(db=self.db, hf_token=hf_token)
                if len(voice_db) > 0:
                    recognizer = VoiceRecognizer(voice_db, hf_token=hf_token)
                    batch = recognizer.identify_dir(recognition_folder)
                    
                    mapping = batch.mapping
                    id_mapping = batch.id_mapping
                    
                    recognition_data.update({
                        "mapping": mapping,
                        "id_mapping": id_mapping,
                        "details": {
                            spk: {
                                "identified": r.best_match, 
                                "voice_id": r.best_match_id,
                                "score": r.best_score
                            }
                            for spk, r in batch.results.items()
                        },
                    })
            
            if recognition_data:
                db_record.recognition_results = cast(Any, recognition_data)
                self.db.commit()

            # Mark as completed
            final_msg = f"Diarização de {clean_title} concluída com sucesso!"
            self.repo.update_status(
                diarization_id, "completed", error_message=None
            )
            self._notify(diarization_id, "completed", final_msg)

            logger.info("Pipeline complete for title=%s", clean_title)
            return {
                "title": clean_title,
                "storage_path": storage_prefix,
                "diarization_result": diarization_result,
                "recognition": recognition_data,
            }
        
        finally:
            # Cleanup local folder
            if video_folder and os.path.exists(video_folder):
                try:
                    shutil.rmtree(video_folder)
                    logger.info(f"Cleaned up temporary video folder: {video_folder}")
                except Exception as cleanup_err:
                    logger.warning(f"Failed to cleanup video folder {video_folder}: {cleanup_err}")
            # Cleanup audio_path if it wasn't moved yet or exists outside video_folder
            if audio_path and os.path.exists(audio_path):
                # Ensure it's not relative to video_folder which was just deleted
                try:
                    if os.path.isfile(audio_path):
                        os.remove(audio_path)
                        logger.info("Cleaned up orphaned audio file: %s", audio_path)
                    elif os.path.isdir(audio_path):
                        shutil.rmtree(audio_path)
                        logger.info("Cleaned up orphaned audio directory: %s", audio_path)
                except Exception as e:
                    logger.warning("Failed to cleanup orphaned audio %s: %s", audio_path, e)
