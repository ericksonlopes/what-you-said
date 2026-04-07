from datetime import datetime, timezone

import pytest

from src.domain.entities.user import User
from src.infrastructure.repositories.sql.user_repository import UserSQLRepository


@pytest.mark.usefixtures("sqlite_memory")
class TestUserRepository:
    @pytest.fixture
    def repository(self):
        return UserSQLRepository()

    def test_create_user(self, repository):
        user = User(
            email="test@example.com",
            full_name="Test User",
            picture_url="http://example.com/pic.jpg",
            created_at=datetime.now(timezone.utc),
            last_login=datetime.now(timezone.utc),
        )

        created_user = repository.create(user)

        assert created_user.id is not None
        assert created_user.email == "test@example.com"
        assert created_user.full_name == "Test User"

    def test_get_by_email(self, repository):
        user = User(
            email="findme@example.com",
            full_name="Find Me",
            created_at=datetime.now(timezone.utc),
            last_login=datetime.now(timezone.utc),
        )
        repository.create(user)

        found_user = repository.get_by_email("findme@example.com")

        assert found_user is not None
        assert found_user.email == "findme@example.com"
        assert found_user.full_name == "Find Me"

    def test_get_by_id(self, repository):
        user = User(
            email="id@example.com",
            full_name="ID User",
            created_at=datetime.now(timezone.utc),
            last_login=datetime.now(timezone.utc),
        )
        created = repository.create(user)

        found_user = repository.get_by_id(created.id)

        assert found_user is not None
        assert found_user.id == created.id
        assert found_user.email == "id@example.com"

    def test_update_last_login(self, repository):
        user = User(
            email="update@example.com",
            full_name="Update User",
            created_at=datetime.now(timezone.utc),
            last_login=datetime.now(timezone.utc),
        )
        created = repository.create(user)
        old_login = created.last_login

        updated_user = repository.update_last_login(created.id)

        assert updated_user.last_login > old_login
