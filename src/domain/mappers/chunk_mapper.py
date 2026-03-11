"""Mapper class for Chunk entity <-> ChunkModel persistence.

This module exposes a single class with static methods to convert between
the domain Chunk entity and the persistence ChunkModel used by repositories.
"""

from typing import Any, Dict
from uuid import uuid4

from langchain_core.documents import Document

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

    @staticmethod
    def document_to_model(document: Document) -> ChunkModel:
        """Convert a langchain Document into a ChunkModel.

        Accepts langchain Document which has page_content and metadata (dict).
        Only include fields in data if they are present and valid. Avoid passing None-valued keys
        to ChunkModel so pydantic defaults (like id default_factory) apply.
        """
        metadata = dict(getattr(document, "metadata", {}) or {})
        # prefer page_content, fall back to content
        content = getattr(document, "page_content", None) or getattr(document, "content", None)
        data = metadata.copy()
        if content is not None:
            data["content"] = content

        # Convert UUID-like fields if present and valid, otherwise remove them
        for key in ["id", "job_id", "content_source_id", "subject_id"]:
            val = data.get(key)
            conv = ChunkMapper._convert_to_uuid(val)
            if conv is not None:
                data[key] = conv
            else:
                data.pop(key, None)

        # Normalize source_type to canonical string (attempt to map to enum values)
        source = data.get("source_type")
        if isinstance(source, ExternalSourceEnum):
            data["source_type"] = source.value
        elif isinstance(source, str):
            norm = ChunkMapper._normalize_source_type(source)
            if norm is not None:
                data["source_type"] = norm
            else:
                data.pop("source_type", None)

        # Ensure required fields for ChunkModel exist: job_id and content_source_id are required,
        # generate them if missing to produce a valid ChunkModel.
        from uuid import uuid4
        if "job_id" not in data:
            data["job_id"] = uuid4()
        if "content_source_id" not in data:
            data["content_source_id"] = uuid4()

        # ChunkModel will generate a new id if none provided (default_factory), so do not pass id=None.
        return ChunkModel(**data)

    @staticmethod
    def _convert_to_uuid(value: Any) -> Any:
        """Convert a value to UUID if it's a valid UUID string, else return None."""
        from uuid import UUID
        if isinstance(value, str):
            try:
                return UUID(value)
            except ValueError:
                return None
        return value

    @staticmethod
    def _normalize_source_type(source: str) -> str:
        """Normalize the source type to the canonical string value used for persistence.

        Tries to map by enum member name (case-insensitive) or by enum value. If mapping fails, returns the input string.
        """
        s = source.strip()
        # try by name (case-insensitive)
        try:
            return ExternalSourceEnum[s.upper()].value
        except Exception:
            pass
        # try match to value ignoring case
        for member in ExternalSourceEnum:
            if member.value.lower() == s.lower() or member.name.lower() == s.lower():
                return member.value
        # fallback: return original string
        return s
