import logging
from sqlalchemy.orm import Session
from src.infrastructure.repositories.storage.storage import StorageService
from src.infrastructure.repositories.sql.repositories import DiarizationRepository

logger = logging.getLogger(__name__)


class ListS3AudioFilesUseCase:
    def __init__(self, db: Session, storage: StorageService | None = None):
        self.db = db
        self.storage = storage or StorageService()
        self.repo = DiarizationRepository(db)

    def execute(self, diarization_id: str, extension: str | None = None) -> list[dict]:
        """
        Lista os arquivos dentro do S3 para um diarization_id específico.
        """
        logger.info("Listing S3 files for diarization_id='%s'", diarization_id)

        record = self.repo.get_by_id(diarization_id)
        if not record:
            raise ValueError(f"Diarization record with id {diarization_id} not found")

        if not record.storage_path:
            logger.warning("Diarization record %s has no storage_path", diarization_id)
            return []

        # Converte s3://bucket/path/to/dir em path/to/dir
        prefix = record.storage_path.replace(f"s3://{self.storage.bucket}/", "")

        try:
            files = self.storage.list_files(prefix=prefix, extension=extension)
            return files
        except Exception as e:
            logger.error("Error listing S3 files: %s", str(e))
            raise e
