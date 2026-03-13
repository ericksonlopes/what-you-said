from typing import Optional, List
from uuid import UUID

from src.config.logger import Logger
from src.domain.entities.content_source_entity import ContentSourceEntity
from src.domain.entities.content_source_status_enum import ContentSourceStatus
from src.domain.entities.source_type_enum_entity import SourceType
from src.domain.mappers.content_source_mapper import ContentSourceMapper
from src.infrastructure.repositories.sql.content_source_repository import ContentSourceSQLRepository


class ContentSourceService:
    """Service layer for content sources.

    Receives a ContentSourceSQLRepository and returns domain entities as outputs.
    """

    def __init__(self, repository: ContentSourceSQLRepository, logger: Optional[Logger] = None) -> None:
        self._repo = repository
        self._logger = logger or Logger()

    def create_source(self, subject_id: Optional[UUID],
                      source_type: SourceType, external_source: str,
                      status: ContentSourceStatus,
                      title: Optional[str] = None,
                      language: Optional[str] = None,
                      embedding_model: Optional[str] = None,
                      dimensions: Optional[int] = None,

                      ) -> ContentSourceEntity:
        """Create a content source and return a domain entity."""
        self._logger.info("Creating content source", context={"external_source": external_source})
        created_id = self._repo.create(subject_id=subject_id, source_type=source_type.value,
                                       external_source=external_source, title=title, language=language,
                                       embedding_model=embedding_model, dimensions=dimensions,
                                       status=(status.value if status is not None else None))
        model = self._repo.get_by_id(created_id)
        entity = ContentSourceMapper.model_to_entity(model)
        assert entity is not None
        return entity

    def get_by_source_info(self, source_type: SourceType, external_source: str) -> Optional[ContentSourceEntity]:
        """Get a content source by its source_type and external_source."""
        self._logger.info("Getting content source by source_type and external_source",
                          context={"source_type": source_type.value, "external_source": external_source})
        list_models = self._repo.get_by_source_info(source_type=source_type.value, external_source=external_source)

        return ContentSourceMapper.model_to_entity(list_models[0]) if list_models else None


    def get_by_id(self, id: UUID) -> Optional[ContentSourceEntity]:
        model = self._repo.get_by_id(id)
        return ContentSourceMapper.model_to_entity(model)

    def list_by_subject(self, subject_id: UUID) -> List[ContentSourceEntity]:
        models = self._repo.list_by_subject(subject_id)
        return ContentSourceMapper.model_list_to_entities(models)

    def update_processing_status(self, content_source_id: UUID, status: ContentSourceStatus) -> None:
        """Update the processing_status field for a content source.

        Accepts a ContentSourceStatus enum and persists its string value to the repository.
        """
        self._repo.update_status(content_source_id=content_source_id, status=status.value)

    def finish_ingestion(self, content_source_id: UUID, embedding_model: str, dimensions: int, chunks: int) -> None:
        """Update the content source record when ingestion is finished."""
        self._repo.finish_ingestion(content_source_id=content_source_id, embedding_model=embedding_model,
                                    dimensions=dimensions, chunks=chunks)
