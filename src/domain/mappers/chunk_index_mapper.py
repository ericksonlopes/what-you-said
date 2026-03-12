from datetime import datetime
from typing import Optional, List, cast
from uuid import UUID

from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.entities.source_type_enum_entity import SourceType
from src.infrastructure.repositories.sql.models.chunk_index import ChunkIndexModel


def _resolve_source_type(s: Optional[str]) -> SourceType:
    """Resolve a SourceType from a string in a clear, deterministic manner.

    This helper lives at module level so the main mapper method remains simple
    and easier to test. It attempts value and name-based resolution, then
    falls back to case-insensitive matching of name or value, and finally to
    the first enum member as a default.
    """
    default = list(SourceType)[0]
    if not s:
        return default

    try:
        return SourceType(s)
    except ValueError:
        pass

    try:
        return SourceType[s]
    except KeyError:
        pass

    s_norm = s.strip().lower()
    for member in SourceType:
        if member.value.lower() == s_norm or member.name.lower() == s_norm:
            return member

    return default


def _extract_cs_metadata(model: ChunkIndexModel) -> dict:
    """Safely extract related ContentSource metadata from a ChunkIndexModel.

    Returning a small dict keeps downstream code simple and avoids
    repeated getattr/conditional logic inside the main mapper.
    """
    cs = getattr(model, "content_source", None)
    return {
        "source_type_str": getattr(cs, "source_type", None),
        "external_source": getattr(cs, "external_source", None),
        "subject_id": getattr(cs, "subject_id", None),
        "embedding_model": getattr(cs, "embedding_model", None),
    }


def _build_entity_kwargs(model: ChunkIndexModel, cs_meta: dict, source_type: SourceType) -> dict:
    """Construct keyword args for ChunkEntity from model and extracted metadata.

    Having this in a helper reduces the number of expressions inside the main
    mapper method and makes the mapping easier to test.
    """
    return {
        "id": cast(UUID, getattr(model, "id")),
        "job_id": cast(Optional[UUID], getattr(model, "job_id", None)),
        "content_source_id": cast(Optional[UUID], getattr(model, "content_source_id", None)),
        "source_type": source_type,
        "external_source": cast(Optional[str], cs_meta.get("external_source") or getattr(model, "chunk_id", None)),
        "subject_id": cast(Optional[UUID], cs_meta.get("subject_id")),
        "content": None,
        "extra": {"chunk_id": getattr(model, "chunk_id", None)},
        "language": cast(Optional[str], getattr(model, "language", None)),
        "embedding_model": cast(Optional[str], cs_meta.get("embedding_model")),
        "created_at": cast(datetime, getattr(model, "created_at")),
        "version_number": cast(int, getattr(model, "version_number", 1)),
    }


class ChunkIndexMapper:
    """Mapper for converting ChunkIndex SQL models into domain ChunkEntity objects.

    The SQL ChunkIndexModel stores index metadata; the mapper extracts available
    information (including related ContentSource when loaded) and constructs a
    ChunkEntity. Missing fields (like content) are left as None since chunk
    content is stored in the vector/doc store.
    """

    @staticmethod
    def model_to_entity(model: Optional[ChunkIndexModel]) -> Optional[ChunkEntity]:
        if model is None:
            return None
        cs_meta = _extract_cs_metadata(model)
        source_type = _resolve_source_type(cs_meta.get("source_type_str"))
        kwargs = _build_entity_kwargs(model, cs_meta, source_type)
        return ChunkEntity(**kwargs)

    @staticmethod
    def model_list_to_entities(models: List[ChunkIndexModel]) -> List[ChunkEntity]:
        temp = [ChunkIndexMapper.model_to_entity(m) for m in models if m is not None]
        return [r for r in temp if r is not None]
