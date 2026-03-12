"""
ORM models for ingestion_jobs table.
"""

import uuid

from sqlalchemy import Column, Text, DateTime, func, ForeignKey, UUID
from sqlalchemy.orm import relationship

from src.infrastructure.repositories.sql.connector import Base


class IngestionJobModel(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    content_source_id = Column(
        UUID,
        ForeignKey("content_sources.id", deferrable=True, initially="IMMEDIATE"),
        nullable=True,
    )
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Text, nullable=False)
    error_message = Column(Text, nullable=True)
    
    embedding_model = Column(Text, nullable=True)
    pipeline_version = Column(Text, nullable=True)

    content_source = relationship("ContentSourceModel", back_populates="ingestion_jobs")
    chunks = relationship("ChunkIndexModel", back_populates="job", cascade="all, delete-orphan")
