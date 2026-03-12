from typing import Optional, List

from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.entities.source_type_enum_entity import SourceType
from src.infrastructure.repositories.sql.models.chunk_index import ChunkIndexModel


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

        # Try to derive source_type and other metadata from the related content_source
        source_type_str = None
        external_source = None
        subject_id = None
        embedding_model = None
        if hasattr(model, "content_source") and model.content_source is not None:
            cs = model.content_source
            source_type_str = getattr(cs, "source_type", None)
            external_source = getattr(cs, "external_source", None)
            subject_id = getattr(cs, "subject_id", None)
            embedding_model = getattr(cs, "embedding_model", None)

        # Convert source_type string to SourceType enum; fall back to first enum member
        source_type = None
        if source_type_str:
            try:
                source_type = SourceType(source_type_str)
            except Exception:
                try:
                    source_type = SourceType[source_type_str]
                except Exception:
                    for member in SourceType:
                        if member.value.lower() == source_type_str.lower() or member.name.lower() == source_type_str.lower():
                            source_type = member
                            break
        if source_type is None:
            source_type = list(SourceType)[0]

        return ChunkEntity(
            id=model.id,
            job_id=getattr(model, "job_id", None),
            content_source_id=getattr(model, "content_source_id", None),
            source_type=source_type,
            external_source=external_source or getattr(model, "chunk_id", None),
            subject_id=subject_id,
            content=None,
            extra={"chunk_id": getattr(model, "chunk_id", None)},
            language=getattr(model, "language", None),
            embedding_model=embedding_model,
            created_at=getattr(model, "created_at", None),
            version_number=getattr(model, "version_number", 1),
        )

    @staticmethod
    def model_list_to_entities(models: List[ChunkIndexModel]) -> List[ChunkEntity]:
        return [ChunkIndexMapper.model_to_entity(m) for m in models if m is not None]
