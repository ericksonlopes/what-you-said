import logging
import traceback
from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from src.application.dtos.commands.process_audio_command import ProcessAudioCommand
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
from src.domain.interfaces.services.i_task_queue import ITaskQueue
from src.presentation.api.dependencies import get_db, get_task_queue_service
from src.presentation.api.schemas.audio_processing_requests import (
    AudioProcessingRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("")
async def start_audio_processing_pipeline(
    request: AudioProcessingRequest,
    task_queue: Annotated[ITaskQueue, Depends(get_task_queue_service)],
):
    logger.info(
        "Audio processing request received: source_type=%s, source=%s",
        request.source_type.value,
        request.source,
    )

    cmd = ProcessAudioCommand(
        source_type=request.source_type.value,
        source=request.source,
        language=request.language or "pt",
        num_speakers=request.num_speakers,
        min_speakers=request.min_speakers,
        max_speakers=request.max_speakers,
        model_size=request.model_size or "large-v2",
        recognize_voices=request.recognize_voices
        if request.recognize_voices is not None
        else True,
    )

    task_queue.enqueue(
        run_audio_diarization_worker,
        cmd,
        task_title=f"Audio diarization: {request.source_type.value}",
        metadata={"source": request.source},
    )

    return {
        "message": "Audio processing started in background.",
        "source_type": request.source_type.value,
        "source": request.source,
    }


@router.post(
    "/{diarization_id}/recognize",
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)
async def identify_speakers_in_existing_diarization(
    diarization_id: str, db: Annotated[Session, Depends(get_db)]
):
    logger.info("Speaker recognition request for diarization_id=%s", diarization_id)
    try:
        use_case = IdentifySpeakersInProcessedAudioUseCase(db)
        return use_case.execute(diarization_id)
    except ValueError as e:
        logger.warning("Recognition failed (ValueError): %s", str(e))
        raise HTTPException(
            status_code=404 if "not found" in str(e) else 400, detail=str(e)
        )
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
    db: Annotated[Session, Depends(get_db)],
    extension: str | None = None,
):
    """
    Lista os arquivos de áudio disponíveis no S3 para um diarization_id específico.
    """
    try:
        use_case = ListS3AudioFilesUseCase(db)
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
    diarization_id: str, speaker_label: str, db: Annotated[Session, Depends(get_db)]
):
    try:
        use_case = GenerateSpeakerAudioAccessUrlUseCase(db)
        return use_case.execute(diarization_id, speaker_label)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            "Presigned URL generation failed: %s\n%s", str(e), traceback.format_exc()
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def retrieve_all_processed_audio_history(
    db: Annotated[Session, Depends(get_db)], limit: int = 10, offset: int = 0
):
    use_case = RetrieveProcessedAudioHistoryUseCase(db)
    return use_case.execute(limit=limit, offset=offset)
