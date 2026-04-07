"""
ORM models for diarization and voice recognition tables.
"""

import datetime
import uuid

from sqlalchemy import JSON, Column, DateTime, String

from src.infrastructure.repositories.sql.connector import Base


def _generate_uuid() -> str:
    return str(uuid.uuid4())


class VoiceRecord(Base):
    __tablename__ = "voices"

    id = Column(String, primary_key=True, default=_generate_uuid)
    name = Column(String, unique=True, index=True)
    embedding = Column(JSON)
    audios_path = Column(String)  # S3 directory prefix where audio samples are stored (e.g. "voices/{id}/")
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))
