from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select

from src.domain.entities.user import User as UserEntity
from src.domain.interfaces.repository.user_repository import IUserRepository
from src.infrastructure.connectors.connector_sql import Connector
from src.infrastructure.repositories.sql.models.user import User as UserModel
from src.infrastructure.repositories.sql.utils.utils import ensure_uuid


class UserSQLRepository(IUserRepository):
    def __init__(self, session_provider: Optional[Connector] = None):
        self._session_provider = session_provider or Connector()

    def _to_entity(self, model: UserModel) -> UserEntity:
        return UserEntity(
            id=model.id,
            email=model.email,
            full_name=model.full_name,
            picture_url=model.picture_url,
            created_at=model.created_at,
            last_login=model.last_login,
        )

    def get_by_email(self, email: str) -> Optional[UserEntity]:
        with self._session_provider as session:
            stmt = select(UserModel).where(UserModel.email == email)
            result = session.execute(stmt).scalar_one_or_none()
            return self._to_entity(result) if result else None

    def get_by_id(self, user_id: Any) -> Optional[UserEntity]:
        user_id = ensure_uuid(user_id)
        if user_id is None:
            return None
        with self._session_provider as session:
            stmt = select(UserModel).where(UserModel.id == str(user_id))
            result = session.execute(stmt).scalar_one_or_none()
            return self._to_entity(result) if result else None

    def create(self, user: UserEntity) -> UserEntity:
        with self._session_provider as session:
            model = UserModel(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                picture_url=user.picture_url,
                created_at=user.created_at or datetime.now(timezone.utc),
                last_login=user.last_login,
            )
            session.add(model)
            session.commit()
            session.refresh(model)
            return self._to_entity(model)

    def update_last_login(self, user_id: Any) -> Optional[UserEntity]:
        user_id = ensure_uuid(user_id)
        if user_id is None:
            return None
        with self._session_provider as session:
            stmt = select(UserModel).where(UserModel.id == str(user_id))
            model = session.execute(stmt).scalar_one_or_none()
            if model:
                model.last_login = datetime.now(timezone.utc)
                session.commit()
                session.refresh(model)
                return self._to_entity(model)
            return None
