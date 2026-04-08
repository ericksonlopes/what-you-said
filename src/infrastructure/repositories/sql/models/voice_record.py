"""
ORM models for diarization and voice recognition tables.
"""

import datetime
import uuid

from sqlalchemy import JSON, Column, DateTime, String

from src.infrastructure.connectors.connector_sql import Base


def _generate_uuid() -> str:
    return str(uuid.uuid4())


class VoiceRecord(Base):
    __tablename__ = "voices"

    id = Column(String, primary_key=True, default=_generate_uuid)
    name = Column(String, unique=True, index=True)
    embedding = Column(JSON)
    audios_path = Column(String)  # S3 directory prefix where audio samples are stored (e.g. "voices/{id}/")
    # Lifecycle status: "processing" (training/reinforcing in background),
    # "ready" (usable), "failed" (training error). Nullable for legacy rows.
    status = Column(String, nullable=True, default="ready")
    status_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.UTC))
