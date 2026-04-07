import logging
import os
import shutil

from sqlalchemy.orm import Session

from src.infrastructure.repositories.sql.diarization_repository import (
    DiarizationRepository,
)
from src.infrastructure.repositories.storage.storage import StorageService
from src.infrastructure.services.content_source_service import ContentSourceService

logger = logging.getLogger(__name__)


class DeleteDiarizationUseCase:
    def __init__(
        self,
        db: Session,
        cs_service: ContentSourceService,
        storage_service: StorageService | None = None,
    ):
        self.db = db
        self.repo = DiarizationRepository(db)
        self.cs_service = cs_service
        self.storage = storage_service or StorageService()

    def execute(self, diarization_id: str) -> bool:
        """
        Deletes a diarization record, its files in S3 and local files.
        """
        logger.info("Starting deletion process for diarization_id=%s", diarization_id)

        record = self.repo.get_by_id(diarization_id)
        if not record:
            logger.warning("Diarization record not found: %s", diarization_id)
            return False

        # 0. Delete associated ContentSource (Cascading deletion)
        try:
            source = self.cs_service.get_by_diarization_id(diarization_id)
            if source:
                logger.info("Found associated ContentSource %s. Deleting...", source.id)
                self.cs_service.delete_source(source.id)
        except Exception as e:
            logger.error(
                "Failed to delete associated ContentSource for diarization %s: %s",
                diarization_id,
                str(e),
            )

        # 1. Delete from S3
        if record.storage_path:
            try:
                # Normalizes prefix (removes S3 bucket prefix if present)
                prefix = record.storage_path.replace(f"s3://{self.storage.bucket}/", "")
                logger.info("Deleting S3 objects with prefix: %s", prefix)
                self.storage.delete_directory(prefix)
            except Exception as e:
                logger.error(
                    "Failed to delete S3 objects for diarization %s: %s",
                    diarization_id,
                    str(e),
                )

        # 2. Delete local folder
        if record.folder_path and os.path.exists(record.folder_path):
            try:
                logger.info("Deleting local folder: %s", record.folder_path)
                if os.path.isdir(record.folder_path):
                    shutil.rmtree(record.folder_path)
                else:
                    os.remove(record.folder_path)
            except Exception as e:
                logger.error(
                    "Failed to delete local folder %s: %s", record.folder_path, str(e)
                )

        # 3. Delete from Database
        logger.info("Deleting database record: %s", diarization_id)
        deleted = self.repo.delete(diarization_id)

        return deleted
