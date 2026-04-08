"""
ORM models for knowledge_subjects table.
"""

import uuid

from sqlalchemy import UUID, Column, DateTime, Text, func
from sqlalchemy.orm import relationship

from src.infrastructure.connectors.connector_sql import Base


class KnowledgeSubjectModel(Base):
    __tablename__ = "knowledge_subjects"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    external_ref = Column(Text, nullable=True)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships (string-based names avoid import-order issues)
    content_sources = relationship("ContentSourceModel", back_populates="subject", cascade="all, delete-orphan")
