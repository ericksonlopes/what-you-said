from typing import Optional, List, Any, cast
from uuid import UUID

from src.infrastructure.repositories.sql.utils import ensure_uuid

from sqlalchemy.orm import selectinload

from src.config.logger import Logger
from src.infrastructure.repositories.sql.connector import Connector
from src.infrastructure.repositories.sql.models.knowledge_subject import (
    KnowledgeSubjectModel,
)

logger = Logger()


class KnowledgeSubjectSQLRepository:
    """Repository helpers for knowledge_subjects table."""

    def create_subject(
        self,
        name: str,
        external_ref: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> UUID:
        with Connector() as session:
            try:
                logger.debug(
                    "Creating KnowledgeSubject",
                    context={
                        "name": name,
                        "external_ref": external_ref,
                        "description": description,
                        "icon": icon,
                    },
                )
                ks = KnowledgeSubjectModel(
                    external_ref=external_ref,
                    name=name,
                    description=description,
                    icon=icon,
                )
                session.add(ks)
                session.commit()
                session.refresh(ks)
                logger.debug(
                    "KnowledgeSubject created successfully", context={"id": ks.id}
                )

                return cast(UUID, ks.id)
            except Exception as e:
                logger.error(
                    "Error creating KnowledgeSubject",
                    context={
                        "name": name,
                        "external_ref": external_ref,
                        "description": description,
                        "error": str(e),
                    },
                )
                session.rollback()
                raise

    def get_by_id(self, ks_id: Any) -> Optional[KnowledgeSubjectModel]:
        ks_id = ensure_uuid(ks_id)
        if ks_id is None:
            return None
        with Connector() as session:
            try:
                logger.debug("Fetching KnowledgeSubject by ID", context={"id": ks_id})
                result = (
                    session.query(KnowledgeSubjectModel)
                    .options(selectinload(KnowledgeSubjectModel.content_sources))
                    .filter_by(id=ks_id)
                    .first()
                )
                logger.debug(
                    "Fetch successful get_by_id",
                    context={"id": ks_id, "result": result},
                )
                return result
            except Exception as e:
                logger.error(
                    "Error fetching KnowledgeSubject by ID",
                    context={"id": id, "error": str(e)},
                )
                raise

    def get_by_external_ref(self, external_ref: str) -> Optional[KnowledgeSubjectModel]:
        with Connector() as session:
            try:
                logger.debug(
                    "Fetching KnowledgeSubject by external_ref",
                    context={"external_ref": external_ref},
                )
                result = (
                    session.query(KnowledgeSubjectModel)
                    .options(selectinload(KnowledgeSubjectModel.content_sources))
                    .filter_by(external_ref=external_ref)
                    .first()
                )
                logger.debug(
                    "Fetch successful get_by_external_ref",
                    context={"external_ref": external_ref, "result": result},
                )
                return result
            except Exception as e:
                logger.error(
                    "Error fetching KnowledgeSubject by external_ref",
                    context={"external_ref": external_ref, "error": str(e)},
                )
                raise

    def list(self, limit: int = 100) -> List[KnowledgeSubjectModel]:
        with Connector() as session:
            try:
                logger.debug("Listing KnowledgeSubjects", context={"limit": limit})
                result = (
                    session.query(KnowledgeSubjectModel)
                    .options(selectinload(KnowledgeSubjectModel.content_sources))
                    .order_by(KnowledgeSubjectModel.created_at.desc())
                    .limit(limit)
                    .all()
                )
                logger.debug(
                    "List successful", context={"limit": limit, "count": len(result)}
                )
                return result
            except Exception as e:
                logger.error(
                    "Error listing KnowledgeSubjects",
                    context={"limit": limit, "error": str(e)},
                )
                raise

    def update(
        self,
        id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        external_ref: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> None:
        with Connector() as session:
            try:
                logger.debug(
                    "Updating KnowledgeSubject",
                    context={
                        "id": id,
                        "name": name,
                        "description": description,
                        "external_ref": external_ref,
                        "icon": icon,
                    },
                )
                ks = session.get(KnowledgeSubjectModel, id)
                if ks is None:
                    logger.warning(
                        "KnowledgeSubject not found for update", context={"id": id}
                    )
                    return
                if name is not None:
                    ks.name = name
                if description is not None:
                    ks.description = description
                if external_ref is not None:
                    ks.external_ref = external_ref
                if icon is not None:
                    ks.icon = icon
                session.commit()
                logger.debug(
                    "KnowledgeSubject updated successfully", context={"id": id}
                )
            except Exception as e:
                logger.error(
                    "Error updating KnowledgeSubject",
                    context={
                        "id": id,
                        "name": name,
                        "description": description,
                        "external_ref": external_ref,
                        "error": str(e),
                    },
                )
                session.rollback()
                raise

    def delete(self, id: UUID) -> int:
        with Connector() as session:
            try:
                logger.debug("Deleting KnowledgeSubject", context={"id": id})
                ks = session.get(KnowledgeSubjectModel, id)
                if ks:
                    session.delete(ks)
                    session.commit()
                    logger.debug(
                        "KnowledgeSubject deleted successfully",
                        context={"id": id, "deleted_count": 1},
                    )
                    return 1
                return 0
            except Exception as e:
                logger.error(
                    "Error deleting KnowledgeSubject",
                    context={"id": id, "error": str(e)},
                )
                session.rollback()
                raise

    def get_by_name(self, name) -> Optional[KnowledgeSubjectModel]:
        with Connector() as session:
            try:
                logger.debug(
                    "Fetching KnowledgeSubject by name", context={"name": name}
                )
                result = (
                    session.query(KnowledgeSubjectModel)
                    .options(selectinload(KnowledgeSubjectModel.content_sources))
                    .filter_by(name=name)
                    .first()
                )
                logger.debug(
                    "Fetch successful", context={"name": name, "result": result}
                )
                return result
            except Exception as e:
                logger.error(
                    "Error fetching KnowledgeSubject by name",
                    context={"name": name, "error": str(e)},
                )
                raise
