from typing import Optional, List, cast
from uuid import UUID
from datetime import datetime

from src.domain.entities.ingestion_job_entity import IngestionJobEntity
from src.domain.entities.enums.ingestion_job_status_enum import IngestionJobStatus
from src.infrastructure.repositories.sql.models.ingestion_job import IngestionJobModel


class IngestionJobMapper:
    @staticmethod
    def model_to_entity(
        model: Optional[IngestionJobModel],
    ) -> Optional[IngestionJobEntity]:
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

        source_title = getattr(model, "source_title", None)
        subject_id = getattr(model, "subject_id", None)

        if hasattr(model, "content_source") and model.content_source:
            if not source_title:
                source_title = getattr(model.content_source, "title", None)
            if not subject_id:
                subject_id = getattr(model.content_source, "subject_id", None)

        return IngestionJobEntity(
            id=cast(UUID, getattr(model, "id")),
            content_source_id=cast(
                Optional[UUID], getattr(model, "content_source_id", None)
            ),
            started_at=cast(datetime, getattr(model, "started_at")),
            created_at=cast(datetime, getattr(model, "created_at")),
            finished_at=cast(Optional[datetime], getattr(model, "finished_at", None)),
            status=status_enum or IngestionJobStatus.STARTED,
            error_message=cast(Optional[str], getattr(model, "error_message", None)),
            status_message=cast(Optional[str], getattr(model, "status_message", None)),
            current_step=cast(Optional[int], getattr(model, "current_step", None)),
            total_steps=cast(Optional[int], getattr(model, "total_steps", None)),
            ingestion_type=cast(Optional[str], getattr(model, "ingestion_type", None)),
            source_title=source_title,
            chunks_count=cast(Optional[int], getattr(model, "chunks_count", None)),
            embedding_model=cast(
                Optional[str], getattr(model, "embedding_model", None)
            ),
            pipeline_version=cast(
                Optional[str], getattr(model, "pipeline_version", None)
            ),
            external_source=cast(
                Optional[str], getattr(model, "external_source", None)
            ),
            subject_id=cast(Optional[UUID], subject_id),
        )

    @staticmethod
    def model_list_to_entities(
        models: List[IngestionJobModel],
    ) -> List[IngestionJobEntity]:
        temp = [
            IngestionJobMapper.model_to_entity(o)
            for o in models
            if o is not None and isinstance(o, IngestionJobModel)
        ]
        return [r for r in temp if r is not None]
