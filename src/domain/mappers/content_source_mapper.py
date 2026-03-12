from typing import Optional, List, Dict, Any

from src.domain.entities.content_source_entity import ContentSourceEntity
from src.infrastructure.repositories.sql.models.content_source import ContentSourceModel


class ContentSourceMapper:
    """Static mapper methods for ContentSource Model <-> Domain Entity."""

    @staticmethod
    def model_to_entity(model: Optional[ContentSourceModel]) -> Optional[ContentSourceEntity]:
        if model is None:
            return None
        return ContentSourceEntity(
            id=model.id,
            subject_id=model.subject_id,
            source_type=model.source_type,
            external_source=model.external_source,
            title=model.title,
            language=model.language,
            created_at=model.created_at,
            ingested_at=getattr(model, "ingested_at", None),
            processing_status=getattr(model, "processing_status", "pending"),
        )

    @staticmethod
    def model_list_to_entities(models: List[ContentSourceModel]) -> List[ContentSourceEntity]:
        return [ContentSourceMapper.model_to_entity(o) for o in models if o is not None]

    @staticmethod
    def entity_to_create_payload(entity: ContentSourceEntity) -> Dict[str, Any]:
        return {
            "subject_id": entity.subject_id,
            "source_type": entity.source_type,
            "external_source": entity.external_source,
            "title": entity.title,
            "language": entity.language,
        }
