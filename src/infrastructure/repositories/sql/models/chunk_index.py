"""
ORM models for chunk_index table.
"""

import uuid

from sqlalchemy import Column, Text, DateTime, Integer, func, ForeignKey, text, UUID
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
    chars = Column(Integer, nullable=False, server_default=text("0"))
    language = Column(Text, nullable=True)
    version_number = Column(Integer, nullable=False, server_default=text("1"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    job = relationship("IngestionJobModel", back_populates="chunks")
