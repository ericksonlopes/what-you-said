"""
ORM models for diarization and voice recognition tables.
"""

import datetime
import uuid

from sqlalchemy import Column, String, DateTime, JSON

from src.infrastructure.repositories.sql.connector import Base


def _generate_uuid() -> str:
    return str(uuid.uuid4())


class VoiceRecord(Base):
    __tablename__ = "voices"

    id = Column(String, primary_key=True, default=_generate_uuid)
    name = Column(String, unique=True, index=True)
    embedding = Column(JSON)
    audio_source = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
