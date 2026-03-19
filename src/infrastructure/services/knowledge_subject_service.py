from typing import Optional, List
from uuid import UUID

from src.config.logger import Logger
from src.domain.entities.knowledge_subject_entity import KnowledgeSubjectEntity
from src.domain.mappers.knowledge_subject_mapper import KnowledgeSubjectMapper
from src.infrastructure.repositories.sql.knowledge_subject_repository import (
    KnowledgeSubjectSQLRepository,
)


class KnowledgeSubjectService:
    """Service layer for knowledge subjects.

    This service receives a KnowledgeSubjectSQLRepository (dependency injection) and
    exposes higher-level operations that orchestrate repository calls and apply
    simple business logic (e.g., get-or-create behavior).

    All outputs that represent subject data are returned as KnowledgeSubjectEntity instances.
    """

    def __init__(
        self, repository: KnowledgeSubjectSQLRepository, logger: Optional[Logger] = None
    ) -> None:
        self._repo = repository
        self._logger = logger or Logger()

    def create_subject(
        self,
        name: str,
        external_ref: Optional[str] = None,
        description: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> KnowledgeSubjectEntity:
        """Create a new knowledge subject and return it as a Domain Entity."""
        self._logger.debug(
            "Creating knowledge subject",
            context={"name": name, "external_ref": external_ref, "icon": icon},
        )
        created_id = self._repo.create_subject(
            name=name, external_ref=external_ref, description=description, icon=icon
        )
        model = self._repo.get_by_id(created_id)
        entity = KnowledgeSubjectMapper.model_to_entity(model)
        assert entity is not None
        return entity

    def get_by_name(self, name: str) -> Optional[KnowledgeSubjectEntity]:
        """Fetch a knowledge subject by name and return as an Entity."""
        self._logger.debug("get_by_name", context={"name": name})
        model = self._repo.get_by_name(name)
        return KnowledgeSubjectMapper.model_to_entity(model)

    def get_subject_by_id(self, id: UUID) -> Optional[KnowledgeSubjectEntity]:
        """Fetch a subject by its UUID and return as an Entity."""
        model = self._repo.get_by_id(id)
        return KnowledgeSubjectMapper.model_to_entity(model)

    def get_subject_by_external_ref(
        self, external_ref: str
    ) -> Optional[KnowledgeSubjectEntity]:
        """Fetch a subject by an external reference string and return as an Entity."""
        model = self._repo.get_by_external_ref(external_ref)
        return KnowledgeSubjectMapper.model_to_entity(model)

    def get_or_create_by_external_ref(
        self,
        external_ref: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> KnowledgeSubjectEntity:
        """Return existing subject with external_ref or create a new one.

        If name is not provided when creating, external_ref is used as the name.
        Returns a Domain Entity representing the subject.
        """
        self._logger.debug(
            "get_or_create_by_external_ref", context={"external_ref": external_ref}
        )
        existing = self._repo.get_by_external_ref(external_ref)
        if existing is not None:
            entity = KnowledgeSubjectMapper.model_to_entity(existing)
            assert entity is not None
            return entity

        created_id = self._repo.create_subject(
            name=name or external_ref,
            external_ref=external_ref,
            description=description,
        )
        model = self._repo.get_by_id(created_id)
        entity = KnowledgeSubjectMapper.model_to_entity(model)
        assert entity is not None
        return entity

    def list_subjects(self, limit: int = 100) -> List[KnowledgeSubjectEntity]:
        """List recent subjects up to `limit` and return Domain Entities."""
        models = self._repo.list(limit)
        return KnowledgeSubjectMapper.model_list_to_entities(models)

    def update_subject(
        self,
        id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        external_ref: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> None:
        """Update fields of an existing subject."""
        self._repo.update(
            id=id,
            name=name,
            description=description,
            external_ref=external_ref,
            icon=icon,
        )

    def delete_subject(self, id: UUID) -> int:
        """Delete a subject by id. Returns number of deleted rows (0 or 1)."""
        return self._repo.delete(id)
