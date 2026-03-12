from typing import Optional, List

from src.domain.entities.ingestion_job_entity import IngestionJobEntity
from src.domain.entities.ingestion_job_status_enum import IngestionJobStatus
from src.infrastructure.repositories.sql.models.ingestion_job import IngestionJobModel


class IngestionJobMapper:
    @staticmethod
    def model_to_entity(model: Optional[IngestionJobModel]) -> Optional[IngestionJobEntity]:
        if model is None:
            return None

        # Map string status from DB to IngestionJobStatus enum when possible
        status_value = getattr(model, "status", None)
        status_enum = None
        if status_value is not None:
            try:
                status_enum = IngestionJobStatus(status_value)
            except ValueError:
                status_enum = None

        return IngestionJobEntity(
            id=model.id,
            content_source_id=model.content_source_id,
            started_at=model.started_at,
            finished_at=getattr(model, "finished_at", None),
            status=status_enum or IngestionJobStatus.STARTED,
            error_message=getattr(model, "error_message", None),
            chunks_count=getattr(model, "chunks_count", None),
            embedding_model=getattr(model, "embedding_model", None),
            pipeline_version=getattr(model, "pipeline_version", None),
        )

    @staticmethod
    def model_list_to_entities(models: List[IngestionJobModel]) -> List[IngestionJobEntity]:
        return [IngestionJobMapper.model_to_entity(o) for o in models if o is not None]
