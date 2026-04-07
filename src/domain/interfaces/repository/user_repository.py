from abc import ABC, abstractmethod
from typing import Optional

from src.domain.entities.user import User


class IUserRepository(ABC):
    """Repository port for storing and retrieving User entities."""

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """Retrieves a user by their email address."""
        raise NotImplementedError

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]:
        """Retrieves a user by their unique ID."""
        raise NotImplementedError

    @abstractmethod
    def create(self, user: User) -> User:
        """Persists a new user entity."""
        raise NotImplementedError

    @abstractmethod
    def update_last_login(self, user_id: str) -> Optional[User]:
        """Updates the last login timestamp for a user."""
        raise NotImplementedError
