import logging
import traceback
from typing import Annotated, Any, List, Optional, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.application.dtos.commands.process_audio_command import ProcessAudioCommand
from src.application.use_cases.delete_diarization_use_case import (
    DeleteDiarizationUseCase,
)
from src.application.use_cases.generate_speaker_audio_access_url import (
    GenerateSpeakerAudioAccessUrlUseCase,
)
from src.application.use_cases.identify_speakers_in_processed_audio import (
    IdentifySpeakersInProcessedAudioUseCase,
)
from src.application.use_cases.list_s3_audio_files import ListS3AudioFilesUseCase
from src.application.use_cases.retrieve_processed_audio_history import (
    RetrieveProcessedAudioHistoryUseCase,
)
from src.application.workers import run_audio_diarization_worker
from src.domain.entities.enums.diarization_status_enum import DiarizationStatus
from src.domain.interfaces.services.i_task_queue import ITaskQueue
from src.presentation.api.dependencies import (
    get_db,
    get_delete_diarization_use_case,
    get_generate_speaker_url_use_case,
    get_identify_speakers_use_case,
    get_list_s3_files_use_case,
    get_retrieve_history_use_case,
    get_task_queue_service,
)
from src.presentation.api.schemas.audio_processing_requests import (
    AudioProcessingRequest,
    UpdateDiarizationRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.patch("/{diarization_id}")
async def update_diarization_segments(
    diarization_id: str,
    request: UpdateDiarizationRequest,
    db: Annotated[Session, Depends(get_db)],
    task_queue: Annotated[ITaskQueue, Depends(get_task_queue_service)],
):
    """
    Updates the segments of a diarization and marks it as completed.
    This is used when the user confirms the final transcript.
    """
    from typing import cast

    from src.infrastructure.repositories.sql.diarization_repository import (
        DiarizationRepository,
    )

    try:
        repo = DiarizationRepository(db)
        record = repo.get_by_id(diarization_id)
        if not record:
            raise HTTPException(status_code=404, detail="Diarization not found")

        # Update segments and status
        logger.info("Updating segments for diarization %s", diarization_id)
        record.segments = cast(Any, request.segments)
        record.status = cast(Any, DiarizationStatus.COMPLETED.value)
        db.commit()

        # Trigger ingestion for ContentSource
        try:
            from src.application.dtos.commands.ingest_diarization_command import (
                IngestDiarizationCommand,
            )
            from src.application.workers import run_diarization_ingestion_worker
            from src.infrastructure.repositories.sql.content_source_repository import (
                ContentSourceSQLRepository,
            )

            cs_repo = ContentSourceSQLRepository()
            target_source = cs_repo.get_by_diarization_id(diarization_id)

            if target_source and target_source.subject_id:
                logger.info(
                    "Found ContentSource %s for diarization %s. Triggering ingestion...",
                    target_source.id,
                    diarization_id,
                )

                cmd = IngestDiarizationCommand(
                    diarization_id=UUID(diarization_id),
                    subject_id=cast(UUID, target_source.subject_id),
                    name=cast(Optional[str], target_source.title),
                    language=cast(str, target_source.language or "pt"),
                    source_type=cast(Optional[str], target_source.source_type),
                    external_source=cast(Optional[str], target_source.external_source),
                    source_metadata=cast(Optional[dict[str, Any]], target_source.source_metadata),
                )

                task_queue.enqueue(
                    run_diarization_ingestion_worker,
                    cmd,
                    task_title=f"Indexing: {target_source.title}",
                )
        except Exception as e:
            logger.error("Failed to trigger ingestion for finalized diarization: %s", e)

        return {
            "status": "success",
            "message": "Diarization updated and marked as completed. Indexing started.",
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Failed to update diarization segments: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


@router.post("")
async def start_audio_processing_pipeline(
    request: AudioProcessingRequest,
    db: Annotated[Session, Depends(get_db)],
    task_queue: Annotated[ITaskQueue, Depends(get_task_queue_service)],
):
    logger.info(
        "Audio processing request received: source_type=%s, source=%s",
        request.source_type.value,
        request.source,
    )

    try:
        from src.application.workers import run_audio_diarization_dispatcher_worker
        from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor

        # 1. Normalize source if YouTube
        is_youtube = request.source_type.value == "youtube"
        normalized_source = request.source
        if is_youtube:
            vid_id = YoutubeExtractor.get_video_id(request.source)
            if vid_id:
                normalized_source = vid_id

        # 2. Detect YouTube Playlist/Channel
        is_playlist = "list=" in request.source or "/playlist" in request.source
        is_channel = (
            "/channel/" in request.source
            or "/c/" in request.source
            or "/user/" in request.source
            or "@" in request.source
        )

        if is_youtube and (is_playlist or is_channel):
            logger.info("Playlist/Channel detected, enqueueing dispatcher")
            cmd = ProcessAudioCommand(
                source_type=request.source_type.value,
                source=request.source,  # Keep original URL for dispatcher to extract videos
                language=request.language or "pt",
                num_speakers=request.num_speakers,
                min_speakers=request.min_speakers,
                max_speakers=request.max_speakers,
                model_size=request.model_size or "large-v2",
                recognize_voices=request.recognize_voices if request.recognize_voices is not None else True,
                subject_id=request.subject_id,
            )
            task_queue.enqueue(
                run_audio_diarization_dispatcher_worker,
                cmd,
                task_title=f"Dispatcher: {request.source}",
            )

            # ------------------------------------------

            return {
                "status": "success",
                "message": "Playlist/Channel processing started in background.",
                "source": request.source,
                "is_bulk": True,
            }

        # 3. Standard single video flow
        from src.infrastructure.repositories.sql.diarization_repository import (
            DiarizationRepository,
        )

        repo = DiarizationRepository(db)

        # Check if already exists
        existing = repo.get_by_external_source(
            source_type=request.source_type.value,
            external_source=normalized_source,
            subject_id=request.subject_id,
        )

        if existing and existing.status != DiarizationStatus.FAILED.value:
            logger.info(
                "Found existing diarization %s for source %s. Skipping creation.",
                existing.id,
                normalized_source,
            )
            return {
                "id": existing.id,
                "message": "Content already processed or processing.",
                "source_type": request.source_type.value,
                "source": request.source,
                "status": existing.status,
            }

        record = repo.create_pending(
            name=request.source,
            source_type=request.source_type.value,
            external_source=normalized_source,
            language=request.language or "pt",
            model_size=request.model_size or "base",
            subject_id=request.subject_id,
        )

        cmd = ProcessAudioCommand(
            diarization_id=cast(str, record.id),
            source_type=request.source_type.value,
            source=normalized_source,
            language=request.language or "pt",
            num_speakers=request.num_speakers,
            min_speakers=request.min_speakers,
            max_speakers=request.max_speakers,
            model_size=request.model_size or "large-v2",
            recognize_voices=request.recognize_voices if request.recognize_voices is not None else True,
            subject_id=request.subject_id,
        )

        task_queue.enqueue(
            run_audio_diarization_worker,
            cmd,
            task_title=f"Audio diarization: {request.source_type.value}",
            metadata={"source": request.source},
        )

        # ---------------------------------------

        return {
            "id": record.id,
            "message": "Audio processing started in background.",
            "source_type": request.source_type.value,
            "source": request.source,
        }
    except Exception as e:
        logger.error("Failed to start audio processing: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{diarization_id}/recognize",
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)
async def identify_speakers_in_existing_diarization(
    diarization_id: str,
    use_case: Annotated[IdentifySpeakersInProcessedAudioUseCase, Depends(get_identify_speakers_use_case)],
):
    logger.info("Speaker recognition request for diarization_id=%s", diarization_id)
    try:
        return use_case.execute(diarization_id)
    except ValueError as e:
        logger.warning("Recognition failed (ValueError): %s", str(e))
        raise HTTPException(status_code=404 if "not found" in str(e) else 400, detail=str(e))
    except Exception as e:
        logger.error("Recognition failed: %s\n%s", str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{diarization_id}/s3/list",
    responses={
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)
async def list_available_s3_files_for_recognition(
    diarization_id: str,
    use_case: Annotated[ListS3AudioFilesUseCase, Depends(get_list_s3_files_use_case)],
    extension: str | None = None,
):
    """
    Lista os arquivos de áudio disponíveis no S3 para um diarization_id específico.
    """
    try:
        return use_case.execute(diarization_id=diarization_id, extension=extension)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to list S3 files: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{diarization_id}/audio/{speaker_label}",
    responses={
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)
async def generate_signed_url_for_speaker_audio(
    diarization_id: str,
    speaker_label: str,
    use_case: Annotated[GenerateSpeakerAudioAccessUrlUseCase, Depends(get_generate_speaker_url_use_case)],
):
    try:
        return use_case.execute(diarization_id, speaker_label)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Presigned URL generation failed: %s\n%s", str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def retrieve_all_processed_audio_history(
    use_case: Annotated[RetrieveProcessedAudioHistoryUseCase, Depends(get_retrieve_history_use_case)],
    limit: int = 10,
    offset: int = 0,
    subject_id: Optional[List[str]] = Query(None),
):
    try:
        logger.info(
            "Fetching audio history: limit=%s, offset=%s, subject_id=%s",
            limit,
            offset,
            subject_id,
        )
        result = use_case.execute(limit=limit, offset=offset, subject_id=subject_id)
        logger.info("Audio history returned %d records", len(result))
        return result
    except Exception as e:
        logger.error("Failed to retrieve audio history: %s\n%s", str(e), traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{diarization_id}",
    responses={
        404: {"description": "Not Found"},
    },
)
async def delete_diarization_record(
    diarization_id: str,
    use_case: Annotated[DeleteDiarizationUseCase, Depends(get_delete_diarization_use_case)],
):
    deleted = use_case.execute(diarization_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Diarization record not found")
    return {"status": "success", "message": "Diarization record and its files deleted"}


@router.post("/{diarization_id}/reprocess")
async def reprocess_diarization(
    diarization_id: str,
    db: Annotated[Session, Depends(get_db)],
    task_queue: Annotated[ITaskQueue, Depends(get_task_queue_service)],
):
    """
    Resets a diarization record to PENDING and re-enqueues the background worker.
    """
    from src.infrastructure.repositories.sql.diarization_repository import (
        DiarizationRepository,
    )

    repo = DiarizationRepository(db)
    record = repo.get_by_id(diarization_id)

    if not record:
        raise HTTPException(status_code=404, detail="Diarization not found")

    # 1. Reset state
    repo.reset_for_reprocessing(diarization_id)

    # 2. Re-enqueue
    cmd = ProcessAudioCommand(
        diarization_id=diarization_id,
        source_type=cast(str, record.source_type),
        source=cast(str, record.external_source),
        language=cast(str, record.language or "pt"),
        model_size=cast(str, record.model_size or "large-v3"),
        # We don't have the original speaker count constraints stored as columns,
        # so we use defaults or just let the pipeline auto-detect.
        recognize_voices=True,
        subject_id=str(record.subject_id) if record.subject_id else None,
    )

    task_queue.enqueue(
        run_audio_diarization_worker,
        cmd,
        task_title=f"Reprocess: {record.name or record.external_source}",
        metadata={"source": record.external_source, "reprocessed": True},
    )

    return {
        "status": "success",
        "message": "Diarization reset and re-enqueued for processing.",
        "id": diarization_id,
    }
