import os
import tempfile
from typing import Annotated

import anyio
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.application.dtos.commands.train_voice_command import TrainVoiceCommand
from src.application.use_cases.manage_voice_profiles import (
    DeleteVoiceAudioFileUseCase,
    DeleteVoiceProfileUseCase,
    ListRegisteredVoiceProfilesUseCase,
    ListVoiceAudioFilesUseCase,
    RegisterNewVoiceProfileUseCase,
)
from src.application.workers import run_voice_training_worker
from src.domain.interfaces.services.i_event_bus import IEventBus
from src.domain.interfaces.services.i_task_queue import ITaskQueue
from src.infrastructure.repositories.sql.diarization_repository import (
    DiarizationRepository,
)
from src.infrastructure.repositories.storage.storage import StorageService
from src.presentation.api.dependencies import (
    get_delete_voice_audio_file_use_case,
    get_delete_voice_profile_use_case,
    get_diarization_repo,
    get_event_bus,
    get_list_voice_audio_files_use_case,
    get_list_voice_profiles_use_case,
    get_register_voice_profile_use_case,
    get_task_queue_service,
)
from src.presentation.api.schemas.voice_profile_requests import (
    VoiceProfileRegistrationRequest,
    VoiceProfileTrainingFromSpeakerRequest,
)

router = APIRouter()


@router.post("", responses={400: {"description": "Bad Request"}})
async def register_new_voice_profile(
    request: VoiceProfileRegistrationRequest,
    event_bus: Annotated[IEventBus, Depends(get_event_bus)],
    use_case: Annotated[RegisterNewVoiceProfileUseCase, Depends(get_register_voice_profile_use_case)],
):
    try:
        voice_id = use_case.execute(request.name, request.audio_path)
        # Notify
        event_bus.publish(
            "ingestion_status",
            {"type": "voice", "action": "register", "name": request.name},
        )
        return {"status": "success", "voice_id": voice_id, "name": request.name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload", responses={400: {"description": "Bad Request"}})
async def upload_and_register_new_voice_profile(
    event_bus: Annotated[IEventBus, Depends(get_event_bus)],
    use_case: Annotated[RegisterNewVoiceProfileUseCase, Depends(get_register_voice_profile_use_case)],
    name: str = Form(...),
    file: UploadFile | None = File(None),
):
    if not file or not file.filename or not file.filename.strip():
        raise HTTPException(status_code=400, detail="No filename provided")

    temp_dir = tempfile.mkdtemp()
    # Sanitize the filename to avoid path traversal or restricted character issues
    filename = os.path.basename(file.filename)
    temp_path = os.path.join(temp_dir, filename)
    try:
        async with await anyio.open_file(temp_path, "wb") as buffer:
            while content := await file.read(1024 * 1024):  # 1MB chunks
                await buffer.write(content)

        voice_id = use_case.execute(name, temp_path)
        # Notify
        event_bus.publish("ingestion_status", {"type": "voice", "action": "register", "name": name})
        return {"status": "success", "voice_id": voice_id, "name": name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)


@router.post(
    "/train-from-speaker",
    status_code=202,
    responses={
        202: {"description": "Accepted - Training started in background"},
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)
async def train_voice_profile_from_existing_speaker_segment(
    request: VoiceProfileTrainingFromSpeakerRequest,
    event_bus: Annotated[IEventBus, Depends(get_event_bus)],
    task_queue: Annotated[ITaskQueue, Depends(get_task_queue_service)],
    repo: Annotated[DiarizationRepository, Depends(get_diarization_repo)],
):
    try:
        # 1. Verification
        record = repo.get_by_id(request.diarization_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Diarization not found: {request.diarization_id}")

        # 2. Notify frontend (voice-scoped — do NOT touch the diarization record's
        # status, since voice training is orthogonal to the diarization lifecycle
        # and mutating the record's status corrupts its real state on reload)
        event_bus.publish(
            "ingestion_status",
            {
                "type": "voice",
                "action": "train_started",
                "name": request.name,
                "diarization_id": request.diarization_id,
                "speaker_label": request.speaker_label,
            },
        )

        # 3. Enqueue background task
        cmd = TrainVoiceCommand(
            diarization_id=request.diarization_id,
            speaker_label=request.speaker_label,
            name=request.name,
        )

        task_queue.enqueue(
            run_voice_training_worker,
            cmd,
            task_title=f"Treino de Voz: {request.name}",
        )

        return {
            "status": "success",
            "message": "Treinamento de voz iniciado em segundo plano",
            "name": request.name,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_all_registered_voice_profiles(
    use_case: Annotated[ListRegisteredVoiceProfilesUseCase, Depends(get_list_voice_profiles_use_case)],
):
    return use_case.execute()


@router.delete("/{name}", responses={404: {"description": "Not Found"}})
async def delete_existing_voice_profile(
    name: str,
    event_bus: Annotated[IEventBus, Depends(get_event_bus)],
    use_case: Annotated[DeleteVoiceProfileUseCase, Depends(get_delete_voice_profile_use_case)],
):
    try:
        use_case.execute(name)
        # Notify
        event_bus.publish("ingestion_status", {"type": "voice", "action": "delete", "name": name})
        return {
            "status": "success",
            "message": f"Voice profile '{name}' successfully removed",
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Voice profile '{name}' not found")


@router.get("/{voice_id}/audios")
async def list_voice_audio_files(
    voice_id: str,
    use_case: Annotated[ListVoiceAudioFilesUseCase, Depends(get_list_voice_audio_files_use_case)],
):
    return use_case.execute(voice_id)


@router.delete("/audios/{s3_key:path}", responses={404: {"description": "Not Found"}})
async def delete_voice_audio_file(
    s3_key: str,
    event_bus: Annotated[IEventBus, Depends(get_event_bus)],
    use_case: Annotated[DeleteVoiceAudioFileUseCase, Depends(get_delete_voice_audio_file_use_case)],
):
    try:
        use_case.execute(s3_key)
        # Notify (voice updated)
        event_bus.publish("ingestion_status", {"type": "voice", "action": "audio_deleted"})
        return {"status": "success", "message": "Audio file deleted"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/audios/{s3_key:path}", responses={404: {"description": "Not Found"}})
async def get_voice_audio_url(
    s3_key: str,
):
    """Retorna uma URL assinada para acessar um arquivo de áudio de perfil de voz."""
    try:
        storage = StorageService()
        url = storage.get_presigned_url(s3_key)
        return {"url": url, "s3_key": s3_key}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
