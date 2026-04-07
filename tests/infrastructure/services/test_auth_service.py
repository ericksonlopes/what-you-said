from unittest.mock import MagicMock, patch

import pytest

from src.domain.entities.user import User
from src.infrastructure.services.auth_service import AuthService


@pytest.fixture
def auth_service():
    with patch("src.infrastructure.services.auth_service.settings") as mock_settings:
        mock_settings.auth.google_client_id = "test_id"
        mock_settings.auth.google_client_secret = "test_secret"
        mock_settings.auth.redirect_uri = "http://localhost:3000"
        mock_settings.auth.jwt_secret = "test_jwt_secret"
        mock_settings.auth.jwt_algorithm = "HS256"
        mock_settings.auth.jwt_expire_minutes = 60
        yield AuthService()


class TestAuthService:
    def test_create_access_token(self, auth_service):
        user = User(id="user123", email="test@example.com", full_name="Test User")
        token = auth_service.create_access_token(user)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token_success(self, auth_service):
        user = User(id="user123", email="test@example.com", full_name="Test User")
        token = auth_service.create_access_token(user)
        payload = auth_service.verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"

    def test_verify_token_invalid(self, auth_service):
        payload = auth_service.verify_token("invalid_token")
        assert payload is None

    @pytest.mark.asyncio
    async def test_get_google_auth_url(self, auth_service):
        url = auth_service.get_google_auth_url()
        assert "accounts.google.com" in url
        assert "client_id=test_id" in url
        assert "response_type=code" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A3000" in url

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.post")
    async def test_exchange_code_for_token(self, mock_post, auth_service):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "google_access_token",
            "id_token": "google_id_token",
        }
        mock_post.return_value = mock_response

        tokens = await auth_service.exchange_code_for_token("test_code")

        assert tokens["access_token"] == "google_access_token"
        mock_post.assert_called_once()
