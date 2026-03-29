from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request

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
async def google_login(
    response: Response,
    auth_use_case: AuthUseCase = Depends(get_auth_use_case),
    settings: Settings = Depends(get_settings),
):
    url, state = await auth_use_case.get_login_url()

    # Store state in a secure, HttpOnly cookie for CSRF protection
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        max_age=600,  # 10 minutes
        samesite="lax",
        secure=settings.app.env == "production",
    )

    return {"url": url}


@router.get("/google/callback")
async def google_callback(
    request: Request,
    response: Response,
    code: str = Query(...),
    state: str = Query(None),
    auth_use_case: AuthUseCase = Depends(get_auth_use_case),
):
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Retrieve expected state from cookie
    expected_state = request.cookies.get("oauth_state")

    try:
        result = await auth_use_case.handle_google_callback(
            code=code, received_state=state, expected_state=expected_state
        )

        # Clear the state cookie
        response.delete_cookie(key="oauth_state")

        # Frontend handles storing the token from the response
        return result
    except Exception as e:
        # Also clear state cookie on failure
        response.delete_cookie(key="oauth_state")
        raise HTTPException(status_code=400, detail=str(e))
