import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi.testclient import TestClient
from main import app
from src.presentation.api.dependencies import get_auth_use_case, get_current_user
from src.domain.entities.user import User

client = TestClient(app)


@pytest.fixture
def mock_auth_use_case():
    mock = MagicMock()
    app.dependency_overrides[get_auth_use_case] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_auth_use_case, None)


@pytest.fixture
def mock_current_user():
    user = User(id="u123", email="test@example.com", full_name="Test User")
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


class TestAuthRouter:
    def test_get_config(self):
        # We need to mock the settings within the router if it uses it directly,
        # but here it uses the use_case or just returns config.
        # Actually /rest/auth/config returns settings.auth.dict()
        response = client.get("/rest/auth/config")
        assert response.status_code == 200
        assert "enable_google" in response.json()

    def test_get_me_success(self, mock_current_user):
        response = client.get("/rest/auth/me")
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    def test_get_me_unauthorized(self):
        # Explicitly override with a failing dependency to test unauthorized access
        from fastapi import HTTPException

        def fail_auth():
            raise HTTPException(status_code=401, detail="Authentication required")

        app.dependency_overrides[get_current_user] = fail_auth
        try:
            response = client.get("/rest/auth/me")
            assert response.status_code == 401
        finally:
            # The conftest.py will re-apply its override for next tests if it's autouse
            # but we should clean up our local override.
            app.dependency_overrides.pop(get_current_user, None)

    @pytest.mark.asyncio
    async def test_google_login(self, mock_auth_use_case):
        mock_auth_use_case.get_login_url = AsyncMock(
            return_value=("http://google.login", "state123")
        )

        response = client.get("/rest/auth/google/login")

        assert response.status_code == 200
        assert response.json()["url"] == "http://google.login"

    @pytest.mark.asyncio
    async def test_google_callback_success(self, mock_auth_use_case):
        mock_auth_use_case.handle_google_callback = AsyncMock(
            return_value={
                "access_token": "jwt",
                "token_type": "bearer",
                "user": {"email": "test@e.c"},
            }
        )

        response = client.get(
            "/rest/auth/google/callback?code=testcode&state=state123&expected_state=state123"
        )

        assert response.status_code == 200
        assert response.json()["access_token"] == "jwt"
        mock_auth_use_case.handle_google_callback.assert_called_with(
            code="testcode", received_state="state123", expected_state="state123"
        )

    def test_google_callback_missing_code(self):
        response = client.get("/rest/auth/google/callback")
        # FastAPI's Query(...) should return 422 if missing,
        # but we also added a manual check for 400.
        assert response.status_code in [400, 422]
