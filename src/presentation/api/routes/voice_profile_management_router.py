from typing import Annotated

from fastapi import APIRouter, HTTPException, Depends

from src.application.use_cases.manage_voice_profiles import (
    RegisterNewVoiceProfileUseCase,
    ListRegisteredVoiceProfilesUseCase,
    DeleteVoiceProfileUseCase,
    TrainVoiceProfileFromSpeakerSegmentUseCase,
)
from src.presentation.api.dependencies import (
    get_register_voice_profile_use_case,
    get_list_voice_profiles_use_case,
    get_delete_voice_profile_use_case,
    get_train_voice_from_speaker_use_case,
)
from src.presentation.api.schemas.voice_profile_requests import (
    VoiceProfileRegistrationRequest,
    VoiceProfileTrainingFromSpeakerRequest,
)

router = APIRouter()


@router.post("", responses={400: {"description": "Bad Request"}})
async def register_new_voice_profile(
    request: VoiceProfileRegistrationRequest,
    use_case: Annotated[
        RegisterNewVoiceProfileUseCase, Depends(get_register_voice_profile_use_case)
    ],
):
    try:
        voice_id = use_case.execute(
            request.name, request.audio_path, force=request.force
        )
        return {"status": "success", "voice_id": voice_id, "name": request.name}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/train-from-speaker",
    responses={
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    },
)
async def train_voice_profile_from_existing_speaker_segment(
    request: VoiceProfileTrainingFromSpeakerRequest,
    use_case: Annotated[
        TrainVoiceProfileFromSpeakerSegmentUseCase,
        Depends(get_train_voice_from_speaker_use_case),
    ],
):
    try:
        voice_id = use_case.execute(
            diarization_id=request.diarization_id,
            speaker_label=request.speaker_label,
            name=request.name,
            force=request.force,
        )
        return {"status": "success", "voice_id": voice_id, "name": request.name}
    except ValueError as e:
        raise HTTPException(
            status_code=404 if "not found" in str(e) else 400, detail=str(e)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_all_registered_voice_profiles(
    use_case: Annotated[
        ListRegisteredVoiceProfilesUseCase, Depends(get_list_voice_profiles_use_case)
    ],
):
    return use_case.execute()


@router.delete("/{name}", responses={404: {"description": "Not Found"}})
async def delete_existing_voice_profile(
    name: str,
    use_case: Annotated[
        DeleteVoiceProfileUseCase, Depends(get_delete_voice_profile_use_case)
    ],
):
    try:
        use_case.execute(name)
        return {
            "status": "success",
            "message": f"Voice profile '{name}' successfully removed",
        }
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Voice profile '{name}' not found")
