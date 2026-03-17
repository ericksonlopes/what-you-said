"""
ORM models for chunk_index table.
"""

import uuid

from sqlalchemy import (
    Column,
    Text,
    DateTime,
    Integer,
    func,
    ForeignKey,
    text,
    UUID,
    Index,
)
from sqlalchemy.orm import relationship

from src.infrastructure.repositories.sql.connector import Base


class ChunkIndexModel(Base):
    __tablename__ = "chunk_index"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    content_source_id = Column(
        UUID,
        ForeignKey("content_sources.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    job_id = Column(
        UUID,
        ForeignKey("ingestion_jobs.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    chunk_id = Column(Text, nullable=False)
    content = Column(Text, nullable=True)
    chars = Column(Integer, nullable=False, server_default=text("0"))
    tokens_count = Column(Integer, nullable=True)
    language = Column(Text, nullable=True)
    version_number = Column(Integer, nullable=False, server_default=text("1"))
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_chunk_index_content_source_id", "content_source_id"),
        Index("ix_chunk_index_job_id", "job_id"),
        Index("ix_chunk_index_chunk_id", "chunk_id"),
    )

    job = relationship("IngestionJobModel", back_populates="chunks")
    content_source = relationship("ContentSourceModel")
