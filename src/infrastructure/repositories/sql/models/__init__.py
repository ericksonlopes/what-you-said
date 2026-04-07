# Package initializer for SQL ORM models.
# Import each model module so SQLAlchemy's declarative registry sees all mappers
# and string-based relationships can be resolved.

from . import (
    chunk_index,  # noqa: F401
    content_source,  # noqa: F401
    diarization_record,  # noqa: F401
    ingestion_job,  # noqa: F401
    knowledge_subject,  # noqa: F401
    user,  # noqa: F401
    voice_record,
)

__all__ = [
    "knowledge_subject",
    "content_source",
    "ingestion_job",
    "chunk_index",
    "user",
    "diarization_record",
    "voice_record",
]
