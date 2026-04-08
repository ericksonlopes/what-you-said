"""
ORM models for diarization and voice recognition tables.
"""

import datetime
import uuid

from sqlalchemy import JSON, UUID, Column, DateTime, Float, ForeignKey, String

from src.domain.entities.enums.diarization_status_enum import DiarizationStatus
from src.infrastructure.connectors.connector_sql import Base


def _generate_uuid() -> str:
    return str(uuid.uuid4())


class DiarizationRecord(Base):
    __tablename__ = "diarizations"

    id = Column(String, primary_key=True, default=_generate_uuid)
    name = Column(String, index=True)
    subject_id = Column(UUID, ForeignKey("knowledge_subjects.id"), nullable=True, index=True)
    source_type = Column(String)
    external_source = Column(String)
    language = Column(String)
    status = Column(String, default=DiarizationStatus.PENDING.value)
    duration = Column(Float)
    folder_path = Column(String)
    storage_path = Column(String, nullable=True)
    segments = Column(JSON)
    recognition_results = Column(JSON, nullable=True)
    model_size = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    status_message = Column(String, nullable=True)
    source_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))
