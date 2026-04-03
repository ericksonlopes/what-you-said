"""
ORM models for diarization and voice recognition tables.
"""

import datetime
import uuid

from sqlalchemy import Column, String, Float, DateTime, JSON

from src.infrastructure.repositories.sql.connector import Base


def _generate_uuid() -> str:
    return str(uuid.uuid4())


class DiarizationRecord(Base):
    __tablename__ = "diarizations"

    id = Column(String, primary_key=True, default=_generate_uuid)
    title = Column(String, index=True)
    source_type = Column(String)
    external_source = Column(String)
    language = Column(String)
    duration = Column(Float)
    folder_path = Column(String)
    storage_path = Column(String, nullable=True)
    segments = Column(JSON)
    recognition_results = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class VoiceRecord(Base):
    __tablename__ = "voices"

    id = Column(String, primary_key=True, default=_generate_uuid)
    name = Column(String, unique=True, index=True)
    embedding = Column(JSON)
    audio_source = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
