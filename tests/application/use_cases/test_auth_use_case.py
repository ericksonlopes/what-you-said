import pytest
from unittest.mock import MagicMock, AsyncMock
from src.application.use_cases.auth_use_case import AuthUseCase
from src.domain.entities.user import User
from src.domain.exception.auth_exceptions import InvalidStateError


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def mock_service():
    return MagicMock()


@pytest.fixture
def use_case(mock_repo, mock_service):
    return AuthUseCase(mock_repo, mock_service)


class TestAuthUseCase:
    def test_get_login_url(self, use_case, mock_service):
        mock_service.get_google_auth_url.return_value = "http://google.login"

        url, state = use_case.get_login_url()

        assert url == "http://google.login"
        assert len(state) > 0

    @pytest.mark.asyncio
    async def test_handle_google_callback_new_user(
        self, use_case, mock_repo, mock_service
    ):
        # 1. Mock token exchange
        mock_service.exchange_code_for_token = AsyncMock(
            return_value={"access_token": "abc"}
        )

        # 2. Mock user info
        mock_service.get_google_user_info = AsyncMock(
            return_value={
                "email": "new@example.com",
                "name": "New User",
                "picture": "http://img",
            }
        )

        # 3. Mock repository (not found -> create)
        mock_repo.get_by_email.return_value = None
        created_user = User(id="u1", email="new@example.com", full_name="New User")
        mock_repo.create.return_value = created_user

        # 4. Mock JWT creation
        mock_service.create_access_token.return_value = "local_jwt"

        result = await use_case.handle_google_callback("test_code", "state1", "state1")

        assert result["access_token"] == "local_jwt"
        assert result["user"]["email"] == "new@example.com"
        mock_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_google_callback_invalid_state(
        self, use_case, mock_repo, mock_service
    ):
        with pytest.raises(InvalidStateError, match="Invalid authentication state"):
            await use_case.handle_google_callback("test_code", "received", "expected")

    @pytest.mark.asyncio
    async def test_handle_google_callback_existing_user(
        self, use_case, mock_repo, mock_service
    ):
        # 1. Mock token exchange
        mock_service.exchange_code_for_token = AsyncMock(
            return_value={"access_token": "abc"}
        )

        # 2. Mock user info
        mock_service.get_google_user_info = AsyncMock(
            return_value={"email": "existing@example.com", "name": "Existing User"}
        )

        # 3. Mock repository (found -> update login)
        existing_user = User(
            id="u2", email="existing@example.com", full_name="Existing User"
        )
        mock_repo.get_by_email.return_value = existing_user
        mock_repo.update_last_login.return_value = existing_user

        # 4. Mock JWT creation
        mock_service.create_access_token.return_value = "local_jwt"

        result = await use_case.handle_google_callback("test_code", "s", "s")

        assert result["access_token"] == "local_jwt"
        mock_repo.update_last_login.assert_called_once_with("u2")

    def test_verify_session(self, use_case, mock_repo, mock_service):
        mock_service.verify_token.return_value = {"sub": "u123"}
        mock_repo.get_by_id.return_value = User(id="u123", email="t@e.c")

        user = use_case.verify_session("valid_token")

        assert user is not None
        assert user.id == "u123"
        mock_repo.get_by_id.assert_called_with("u123")
