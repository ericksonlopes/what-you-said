"""
ORM models for query_logs table.
"""

import uuid

from sqlalchemy import Column, Text, DateTime, Integer, func, ForeignKey, UUID
from sqlalchemy.orm import relationship

from src.infrastructure.repositories.sql.connector import Base

class QueryLogModel(Base):
    __tablename__ = "query_logs"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    subject_id = Column(
        UUID,
        ForeignKey("knowledge_subjects.id", deferrable=True, initially="IMMEDIATE"),
        nullable=True,
    )
    query_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    top_k = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)

    subject = relationship("KnowledgeSubjectModel")
