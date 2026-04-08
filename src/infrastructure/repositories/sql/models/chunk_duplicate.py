"""
ORM models for chunk_duplicate table.
"""

import uuid

from sqlalchemy import (
    JSON,
    UUID,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Text,
    func,
)

from src.infrastructure.connectors.connector_sql import Base


class ChunkDuplicateModel(Base):
    __tablename__ = "chunk_duplicates"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    chunk_ids = Column(JSON, nullable=False)
    similarity = Column(Float, nullable=False)
    content_source_id = Column(
        UUID,
        ForeignKey("content_sources.id", deferrable=True, initially="IMMEDIATE"),
        nullable=True,
    )
    status = Column(Text, default="pending", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
