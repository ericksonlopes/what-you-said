from typing import List, Optional, cast
from uuid import UUID

from sqlalchemy.orm import Session

from src.domain.entities.diarization import DiarizationResult
from src.domain.entities.enums.diarization_status_enum import DiarizationStatus
from src.infrastructure.repositories.sql.models.diarization_record import (
    DiarizationRecord,
)


class DiarizationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_pending(
        self,
        name: str,
        source_type: str,
        external_source: str,
        language: str,
        model_size: str | None = None,
        subject_id: str | None = None,
    ) -> DiarizationRecord:
        record = DiarizationRecord(
            name=name,
            source_type=source_type,
            external_source=external_source,
            language=language,
            status=DiarizationStatus.PENDING.value,
            model_size=model_size,
            subject_id=UUID(subject_id) if subject_id and isinstance(subject_id, str) else subject_id,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def save(
        self,
        result: DiarizationResult,
        name: str,
        source_type: str,
        external_source: str,
        folder: str,
        storage_path: str | None = None,
        diarization_id: str | None = None,
    ) -> DiarizationRecord:
        if diarization_id:
            db_diarization = self.get_by_id(diarization_id)
            if db_diarization:
                db_diarization.name = name  # type: ignore
                db_diarization.language = result.language  # type: ignore
                db_diarization.duration = result.duration  # type: ignore
                db_diarization.folder_path = folder  # type: ignore
                db_diarization.storage_path = storage_path  # type: ignore
                db_diarization.segments = [seg.to_dict() for seg in result.segments]  # type: ignore
                db_diarization.status = DiarizationStatus.PROCESSING.value  # type: ignore
                self.db.commit()
                self.db.refresh(db_diarization)
                return db_diarization

        db_diarization = DiarizationRecord(
            name=name,
            source_type=source_type,
            external_source=external_source,
            language=result.language,
            duration=result.duration,
            folder_path=folder,
            storage_path=storage_path,  # type: ignore
            segments=[seg.to_dict() for seg in result.segments],
            status=DiarizationStatus.PROCESSING.value,
        )
        self.db.add(db_diarization)
        self.db.commit()
        self.db.refresh(db_diarization)
        return db_diarization

    def update_status(
        self,
        diarization_id: str,
        status: str,
        error_message: str | None = None,
        status_message: str | None = None,
    ) -> Optional[DiarizationRecord]:
        record = self.get_by_id(diarization_id)
        if not record:
            return None
        record.status = status  # type: ignore
        if error_message is not None:
            record.error_message = error_message  # type: ignore
        if status_message is not None:
            record.status_message = status_message  # type: ignore
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_by_external_source(
        self,
        source_type: str,
        external_source: str,
        subject_id: str | object | None = None,
    ) -> Optional[DiarizationRecord]:
        query = self.db.query(DiarizationRecord).filter(
            DiarizationRecord.source_type == source_type,
            DiarizationRecord.external_source == external_source,
        )
        if subject_id:
            parsed_id = UUID(str(subject_id)) if isinstance(subject_id, str) else subject_id
            query = query.filter(DiarizationRecord.subject_id == parsed_id)
        else:
            query = query.filter(DiarizationRecord.subject_id.is_(None))

        result = query.first()
        return cast(Optional[DiarizationRecord], result)

    def get_all(
        self,
        limit: int = 10,
        offset: int = 0,
        subject_id: str | List[str] | None = None,
    ) -> List[DiarizationRecord]:

        query = self.db.query(DiarizationRecord)
        if subject_id:
            if isinstance(subject_id, list):
                parsed_ids = [UUID(sid) if isinstance(sid, str) else sid for sid in subject_id]
                query = query.filter(DiarizationRecord.subject_id.in_(parsed_ids))
            else:
                parsed_id = UUID(subject_id) if isinstance(subject_id, str) else subject_id
                query = query.filter(DiarizationRecord.subject_id == parsed_id)

        result = query.order_by(DiarizationRecord.created_at.desc()).offset(offset).limit(limit).all()
        return cast(List[DiarizationRecord], result)

    def get_by_id(self, diarization_id: str) -> Optional[DiarizationRecord]:
        result = self.db.query(DiarizationRecord).filter(DiarizationRecord.id == diarization_id).first()
        return cast(Optional[DiarizationRecord], result)

    def delete(self, diarization_id: str) -> bool:
        record = self.db.query(DiarizationRecord).filter(DiarizationRecord.id == diarization_id).first()
        if not record:
            return False
        self.db.delete(record)
        self.db.commit()
        return True

    def update_recognition_results(self, diarization_id: str, recognition_results: dict) -> Optional[DiarizationRecord]:
        record = self.get_by_id(diarization_id)
        if not record:
            return None
        record.recognition_results = recognition_results  # type: ignore
        self.db.commit()
        self.db.refresh(record)
        return record

    def reset_for_reprocessing(self, diarization_id: str) -> Optional[DiarizationRecord]:
        """Resets the record for a new diarization run."""
        record = self.get_by_id(diarization_id)
        if not record:
            return None

        record.status = DiarizationStatus.PENDING.value  # type: ignore
        record.error_message = None  # type: ignore
        record.status_message = "Pronto para reprocessamento"  # type: ignore
        record.segments = None  # type: ignore
        record.recognition_results = None  # type: ignore
        record.duration = 0.0  # type: ignore

        self.db.commit()
        self.db.refresh(record)
        return record
