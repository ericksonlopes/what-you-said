from datetime import datetime
from typing import Optional, List, cast
from uuid import UUID

from src.domain.entities.knowledge_subject_entity import KnowledgeSubjectEntity
from src.infrastructure.repositories.sql.models.knowledge_subject import (
    KnowledgeSubjectModel,
)


class KnowledgeSubjectMapper:
    """Static mapper methods for KnowledgeSubject ORM <-> Domain Entity."""

    @staticmethod
    def model_to_entity(
        model: Optional[KnowledgeSubjectModel],
    ) -> Optional[KnowledgeSubjectEntity]:
        if model is None:
            return None
        return KnowledgeSubjectEntity(
            id=cast(UUID, getattr(model, "id")),
            external_ref=cast(Optional[str], getattr(model, "external_ref", None)),
            name=cast(str, getattr(model, "name", "")),
            description=cast(Optional[str], getattr(model, "description", None)),
            icon=cast(Optional[str], getattr(model, "icon", None)),
            source_count=len(getattr(model, "content_sources", [])),
            created_at=cast(datetime, getattr(model, "created_at")),
        )

    @staticmethod
    def model_list_to_entities(
        models: List[KnowledgeSubjectModel],
    ) -> List[KnowledgeSubjectEntity]:
        temp = [
            KnowledgeSubjectMapper.model_to_entity(m) for m in models if m is not None
        ]
        return [r for r in temp if r is not None]
