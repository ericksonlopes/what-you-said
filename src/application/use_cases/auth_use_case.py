from typing import Optional, Dict, Any
from datetime import datetime, timezone

from src.domain.entities.user import User as UserEntity
from src.infrastructure.repositories.sql.user_repository import UserSQLRepository
from src.infrastructure.services.auth_service import AuthService


class AuthUseCase:
    def __init__(
        self,
        user_repo: UserSQLRepository,
        auth_service: AuthService,
    ):
        self._user_repo = user_repo
        self._auth_service = auth_service

    async def get_login_url(self) -> str:
        return await self._auth_service.get_google_auth_url()

    async def handle_google_callback(self, code: str) -> Dict[str, Any]:
        # 1. Exchange code for token
        tokens = await self._auth_service.exchange_code_for_token(code)
        access_token = tokens.get("access_token")
        if not access_token:
            raise ValueError("Failed to obtain access token from Google")

        # 2. Get user info from Google
        google_user = await self._auth_service.get_google_user_info(access_token)
        email = google_user.get("email")
        name = google_user.get("name")
        picture = google_user.get("picture")

        if not email or not name:
            raise ValueError("Google user info missing email or name")

        # 3. Check if user exists, or create new
        user = self._user_repo.get_by_email(email)
        if not user:
            user = UserEntity(
                email=email,
                full_name=name,
                picture_url=picture,
                created_at=datetime.now(timezone.utc),
                last_login=datetime.now(timezone.utc),
            )
            user = self._user_repo.create(user)
        else:
            user = self._user_repo.update_last_login(user.id)

        if not user:
            raise ValueError("Failed to create or retrieve user")

        # 4. Create local JWT
        jwt_token = self._auth_service.create_access_token(user)

        return {
            "access_token": jwt_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "picture_url": user.picture_url,
            },
        }

    def verify_session(self, token: str) -> Optional[UserEntity]:
        payload = self._auth_service.verify_token(token)
        if not payload:
            return None

        user_id = payload.get("sub")
        return self._user_repo.get_by_id(user_id)
