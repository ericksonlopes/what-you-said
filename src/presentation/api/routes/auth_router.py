from typing import Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException, Query

from src.application.use_cases.auth_use_case import AuthUseCase
from src.presentation.api.dependencies import (
    get_auth_use_case,
    get_settings,
    get_current_user,
)
from src.config.settings import Settings
from src.domain.exception.auth_exceptions import AuthDomainError
from src.domain.entities.user import User

router = APIRouter()


@router.get("/config")
async def get_auth_config(settings: Annotated[Settings, Depends(get_settings)]):
    return {
        "enable_google": settings.auth.enable_google,
        "redirect_uri": settings.auth.redirect_uri,
    }


@router.get("/me")
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@router.get("/google/login")
async def google_login(
    auth_use_case: Annotated[AuthUseCase, Depends(get_auth_use_case)],
):
    url, state = auth_use_case.get_login_url()
    return {"url": url, "state": state}


@router.get(
    "/google/callback",
    responses={
        400: {"description": "Missing authorization code or OAuth state mismatch"},
        500: {"description": "Internal server error during authentication"},
    },
)
async def google_callback(
    code: Annotated[str, Query(...)],
    auth_use_case: Annotated[AuthUseCase, Depends(get_auth_use_case)],
    state: Annotated[Optional[str], Query()] = None,
    expected_state: Annotated[Optional[str], Query()] = None,
):
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    try:
        result = await auth_use_case.handle_google_callback(
            code=code,
            received_state=state or "",
            expected_state=expected_state or "",
        )
        return result
    except AuthDomainError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error during auth")
