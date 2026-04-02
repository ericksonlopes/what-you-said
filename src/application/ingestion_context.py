from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.domain.interfaces.services.i_event_bus import IEventBus
from src.infrastructure.services.chunk_index_service import ChunkIndexService
from src.infrastructure.services.content_source_service import ContentSourceService
from src.infrastructure.services.embedding_service import EmbeddingService
from src.infrastructure.services.ingestion_job_service import IngestionJobService
from src.infrastructure.services.knowledge_subject_service import (
    KnowledgeSubjectService,
)
from src.infrastructure.services.model_loader_service import ModelLoaderService

if TYPE_CHECKING:
    from src.config.settings import Settings


@dataclass
class IngestionContext:
    """Groups the common dependencies shared by all ingestion use cases."""

    settings: Settings
    ks_service: KnowledgeSubjectService
    cs_service: ContentSourceService
    job_service: IngestionJobService
    model_loader: ModelLoaderService
    embed_service: EmbeddingService
    chunk_service: ChunkIndexService
    event_bus: IEventBus
    vector_store_type: str
