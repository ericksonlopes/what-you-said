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
