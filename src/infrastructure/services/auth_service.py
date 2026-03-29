from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
from jose import jwt, JWTError

from src.config.settings import settings
from src.domain.entities.user import User as UserEntity


class AuthService:
    def __init__(self):
        self.client_id = settings.auth.google_client_id
        self.client_secret = settings.auth.google_client_secret
        self.redirect_uri = settings.auth.redirect_uri
        self.jwt_secret = settings.auth.jwt_secret
        self.jwt_algorithm = settings.auth.jwt_algorithm
        self.jwt_expire_minutes = settings.auth.jwt_expire_minutes

    async def get_google_auth_url(self) -> str:
        """Returns the URL to redirect the user to for Google Authentication."""
        base_url = "https://accounts.google.com/o/oauth2/v2/auth"
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "select_account",
        }
        from urllib.parse import urlencode
        query_string = urlencode(params)
        return f"{base_url}?{query_string}"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchanges an authorization code for an access token and ID token."""
        url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)
            response.raise_for_status()
            return response.json()

    async def get_google_user_info(self, access_token: str) -> Dict[str, Any]:
        """Fetches user profile information from Google."""
        url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    def create_access_token(self, user: UserEntity) -> str:
        """Generates a local JWT for the user."""
        expire = datetime.now(timezone.utc) + timedelta(minutes=self.jwt_expire_minutes)
        to_encode = {
            "sub": user.id,
            "email": user.email,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
        }
        return jwt.encode(to_encode, self.jwt_secret, algorithm=self.jwt_algorithm)

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verifies a local JWT and returns the payload."""
        try:
            payload = jwt.decode(
                token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )
            return payload
        except JWTError:
            return None
