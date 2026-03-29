from fastapi import APIRouter, Depends, HTTPException, Query

from src.application.use_cases.auth_use_case import AuthUseCase
from src.presentation.api.dependencies import (
    get_auth_use_case,
    get_settings,
    get_current_user,
)
from src.config.settings import Settings
from src.domain.entities.user import User

router = APIRouter()


@router.get("/config")
async def get_auth_config(settings: Settings = Depends(get_settings)):
    return {
        "enable_google": settings.auth.enable_google,
        "redirect_uri": settings.auth.redirect_uri,
    }


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/google/login")
async def google_login(auth_use_case: AuthUseCase = Depends(get_auth_use_case)):
    url = await auth_use_case.get_login_url()
    return {"url": url}


@router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    auth_use_case: AuthUseCase = Depends(get_auth_use_case),
):
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    try:
        result = await auth_use_case.handle_google_callback(code)
        # Frontend handles storing the token from the response
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
