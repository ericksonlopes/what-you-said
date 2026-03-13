"""
ORM models for content_sources table.
"""

import uuid

from sqlalchemy import Column, Text, DateTime, Integer, func, ForeignKey, UUID, text
from sqlalchemy.orm import relationship

from src.infrastructure.repositories.sql.connector import Base

class ContentSourceModel(Base):
    __tablename__ = "content_sources"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    subject_id = Column(
        UUID,
        ForeignKey("knowledge_subjects.id", deferrable=True, initially="IMMEDIATE"),
        nullable=True,
    )
    source_type = Column(Text, nullable=False)
    external_source = Column(Text, nullable=False)
    title = Column(Text, nullable=True)
    language = Column(Text, nullable=True)
    embedding_model = Column(Text, nullable=True)
    dimensions = Column(Integer, nullable=True)
    status = Column(Text, nullable=False, server_default=text("'active'"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ingested_at = Column(DateTime(timezone=True), nullable=True)
    processing_status = Column(Text, nullable=False, default="pending")
    chunks = Column(Integer, nullable=False, server_default=text("0"))
    subject = relationship("KnowledgeSubjectModel", back_populates="content_sources")
    ingestion_jobs = relationship("IngestionJobModel", back_populates="content_source", cascade="all, delete-orphan")