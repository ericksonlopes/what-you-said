from sqlalchemy.orm import Session

from src.domain.entities.enums.diarization_status_enum import DiarizationStatus
from src.infrastructure.repositories.sql.diarization_repository import (
    DiarizationRepository,
)


class RetrieveProcessedAudioHistoryUseCase:
    def __init__(self, db: Session):
        self.repo = DiarizationRepository(db)

    def execute(self, limit: int = 10, offset: int = 0, subject_id: str | list[str] | None = None) -> list[dict]:
        records = self.repo.get_all(limit=limit, offset=offset, subject_id=subject_id)

        return [
            {
                "id": r.id,
                "name": r.name,
                "subject_id": r.subject_id,
                "source_type": r.source_type,
                "external_source": r.external_source,
                "language": r.language,
                "status": r.status or DiarizationStatus.COMPLETED.value,
                "model_size": r.model_size,
                "duration": r.duration,
                "storage_path": r.storage_path,
                "segments": r.segments,
                "recognition_results": r.recognition_results,
                "source_metadata": r.source_metadata,
                "error_message": r.error_message,
                "status_message": r.status_message,
                "created_at": str(r.created_at) if r.created_at else None,
            }
            for r in records
        ]
