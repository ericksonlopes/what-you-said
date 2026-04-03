from sqlalchemy.orm import Session

from src.infrastructure.repositories.sql.repositories import DiarizationRepository


class RetrieveProcessedAudioHistoryUseCase:
    def __init__(self, db: Session):
        self.repo = DiarizationRepository(db)

    def execute(self, limit: int = 10, offset: int = 0) -> list[dict]:
        records = self.repo.get_all(limit=limit, offset=offset)
        return [
            {
                "id": r.id,
                "title": r.title,
                "source_type": r.source_type,
                "external_source": r.external_source,
                "language": r.language,
                "duration": r.duration,
                "storage_path": r.storage_path,
                "recognition_results": r.recognition_results,
                "created_at": str(r.created_at) if r.created_at else None,
            }
            for r in records
        ]
