"""
ORM models for content_sources table.
"""

import uuid

from sqlalchemy import (
    JSON,
    UUID,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import relationship

from src.infrastructure.connectors.connector_sql import Base


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
    status = Column(Text, nullable=False, server_default=text("'active'"))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    ingested_at = Column(DateTime(timezone=True), nullable=True)
    processing_status = Column(Text, nullable=False, default="pending", index=True)
    dimensions = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    max_tokens_per_chunk = Column(Integer, nullable=True)
    chunks = Column(Integer, nullable=False, server_default=text("0"))
    status_message = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    source_metadata = Column(JSON, nullable=True)
    subject = relationship("KnowledgeSubjectModel", back_populates="content_sources")
    ingestion_jobs = relationship(
        "IngestionJobModel",
        back_populates="content_source",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "external_source",
            "subject_id",
            name="uq_content_source_external_source_per_subject",
        ),
        Index("ix_content_sources_subject_id", "subject_id"),
        Index("ix_content_sources_source_type", "source_type"),
        Index("ix_content_sources_status", "status"),
    )
