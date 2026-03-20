from datetime import datetime
from typing import Optional, List, Dict, Any, cast
from uuid import UUID

from src.domain.entities.content_source_entity import ContentSourceEntity
from src.infrastructure.repositories.sql.models.content_source import ContentSourceModel


class ContentSourceMapper:
    """Static mapper methods for ContentSource Model <-> Domain Entity."""

    @staticmethod
    def model_to_entity(
        model: Optional[ContentSourceModel],
    ) -> Optional[ContentSourceEntity]:
        if model is None:
            return None
        return ContentSourceEntity(
            id=cast(UUID, getattr(model, "id")),
            subject_id=cast(Optional[UUID], getattr(model, "subject_id", None)),
            source_type=cast(str, getattr(model, "source_type")),
            external_source=cast(str, getattr(model, "external_source")),
            title=cast(Optional[str], getattr(model, "title", None)),
            language=cast(Optional[str], getattr(model, "language", None)),
            created_at=cast(datetime, getattr(model, "created_at")),
            ingested_at=cast(Optional[datetime], getattr(model, "ingested_at", None)),
            processing_status=cast(str, getattr(model, "processing_status", "pending")),
            embedding_model=cast(
                Optional[str], getattr(model, "embedding_model", None)
            ),
            dimensions=cast(Optional[int], getattr(model, "dimensions", None)),
            total_tokens=cast(Optional[int], getattr(model, "total_tokens", None)),
            max_tokens_per_chunk=cast(
                Optional[int], getattr(model, "max_tokens_per_chunk", None)
            ),
            status=cast(str, getattr(model, "status", "active")),
            chunks=cast(int, getattr(model, "chunks", 0)),
        )

    @staticmethod
    def model_list_to_entities(
        models: List[ContentSourceModel],
    ) -> List[ContentSourceEntity]:
        temp = [ContentSourceMapper.model_to_entity(o) for o in models if o is not None]
        return [r for r in temp if r is not None]

    @staticmethod
    def entity_to_create_payload(entity: ContentSourceEntity) -> Dict[str, Any]:
        return {
            "subject_id": entity.subject_id,
            "source_type": entity.source_type,
            "external_source": entity.external_source,
            "title": entity.title,
            "language": entity.language,
            "embedding_model": entity.embedding_model,
            "dimensions": entity.dimensions,
            "status": entity.status,
            "chunks": entity.chunks,
        }
