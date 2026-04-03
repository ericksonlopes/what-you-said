from typing import List, Optional, cast

from sqlalchemy.orm import Session

from src.domain.entities.diarization import DiarizationResult
from src.infrastructure.repositories.sql.models.diarization import DiarizationRecord


class DiarizationRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(
        self,
        result: DiarizationResult,
        title: str,
        source_type: str,
        external_source: str,
        folder: str,
        storage_path: str | None = None,
    ) -> DiarizationRecord:
        db_diarization = DiarizationRecord(
            title=title,
            source_type=source_type,
            external_source=external_source,
            language=result.language,
            duration=result.duration,
            folder_path=folder,
            storage_path=storage_path,  # type: ignore
            segments=[seg.to_dict() for seg in result.segments],
        )
        self.db.add(db_diarization)
        self.db.commit()
        self.db.refresh(db_diarization)
        return db_diarization

    def get_all(self, limit: int = 10, offset: int = 0) -> List[DiarizationRecord]:
        result = self.db.query(DiarizationRecord).offset(offset).limit(limit).all()
        return cast(List[DiarizationRecord], cast(object, result))

    def get_by_id(self, diarization_id: str) -> Optional[DiarizationRecord]:
        result = (
            self.db.query(DiarizationRecord)
            .filter(DiarizationRecord.id == diarization_id)
            .first()
        )
        return cast(Optional[DiarizationRecord], result)
