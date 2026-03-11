"""Mapper class for Chunk entity <-> ChunkModel persistence.

This module exposes a single class with static methods to convert between
the domain Chunk entity and the persistence ChunkModel used by repositories.
"""

from typing import Any, Dict
from uuid import uuid4

from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.entities.external_source_enum_entity import ExternalSourceEnum
from src.infrastructure.repository.weaviate.model.chunk_model import ChunkModel


class ChunkMapper:
    """Static mapper methods to convert between domain Chunk and persistence ChunkModel."""

    @staticmethod
    def entity_to_model(entity: ChunkEntity) -> ChunkModel:
        """Convert a domain Chunk into a persistence ChunkModel.

        Ensures required identifiers (job_id, content_source_id) exist by generating
        UUIDs when missing. Returns a ChunkModel ready for persistence.
        """
        data: Dict[str, Any] = entity.model_dump()
        if data.get("job_id") is None:
            data["job_id"] = uuid4()
        if data.get("content_source_id") is None:
            data["content_source_id"] = uuid4()
        # ensure source_type is a primitive str for persistence
        source = data.get("source_type")
        if isinstance(source, ExternalSourceEnum):
            data["source_type"] = source.value
        elif isinstance(source, str):
            # try to normalize enum names like 'YOUTUBE' to their values
            try:
                data["source_type"] = ExternalSourceEnum[source].value
            except Exception:
                try:
                    data["source_type"] = ExternalSourceEnum(source).value
                except Exception:
                    pass
        return ChunkModel(**data)

    @staticmethod
    def model_to_entity(model: ChunkModel) -> ChunkEntity:
        """Convert a persistence ChunkModel into a domain Chunk entity."""
        data = model.model_dump()
        source = data.get("source_type")
        if isinstance(source, str):
            try:
                data["source_type"] = ExternalSourceEnum(source)
            except ValueError:
                try:
                    data["source_type"] = ExternalSourceEnum[source]
                except Exception:
                    pass
        return ChunkEntity(**data)
