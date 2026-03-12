from typing import Optional, List

from src.domain.entities.knowledge_subject_entity import KnowledgeSubjectEntity
from src.infrastructure.repositories.sql.models.knowledge_subject import KnowledgeSubjectModel


class KnowledgeSubjectMapper:
    """Static mapper methods for KnowledgeSubject ORM <-> Domain Entity."""

    @staticmethod
    def model_to_entity(model: Optional[KnowledgeSubjectModel]) -> Optional[KnowledgeSubjectEntity]:
        if model is None:
            return None
        return KnowledgeSubjectEntity(
            id=model.id,
            external_ref=model.external_ref,
            name=model.name,
            description=model.description,
            created_at=model.created_at,
        )

    @staticmethod
    def model_list_to_entities(models: List[KnowledgeSubjectModel]) -> List[KnowledgeSubjectEntity]:
        return [KnowledgeSubjectMapper.model_to_entity(m) for m in models if m is not None]
