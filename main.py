import uuid
from datetime import datetime, timezone
from pprint import pprint
from typing import List

from langchain_core.documents import Document

from src.config.logger import Logger
from src.config.settings import settings
from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.entities.content_source_status_enum import ContentSourceStatus
from src.domain.entities.ingestion_job_status_enum import IngestionJobStatus
from src.domain.entities.source_type_enum_entity import SourceType
from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor
from src.infrastructure.repositories.sql.chunk_index_repository import ChunkIndexSQLRepository
from src.infrastructure.repositories.sql.content_source_repository import ContentSourceSQLRepository
from src.infrastructure.repositories.sql.ingestion_job_repository import IngestionJobSQLRepository
from src.infrastructure.repositories.sql.knowledge_subject_repository import KnowledgeSubjectSQLRepository
from src.infrastructure.repositories.vector.weaviate.chunk_repository import ChunkWeaviateRepository
from src.infrastructure.repositories.vector.weaviate.weaviate_client import WeaviateClient
from src.infrastructure.services.chunk_index_service import ChunkIndexService
from src.infrastructure.services.content_source_service import ContentSourceService
from src.infrastructure.services.embeddding_service import EmbeddingService
from src.infrastructure.services.ingestion_job_service import IngestionJobService
from src.infrastructure.services.knowledge_subject_service import KnowledgeSubjectService
from src.infrastructure.services.model_loader_service import ModelLoaderService
from src.infrastructure.services.youtube_data_process_service import YoutubeDataProcessService
from src.infrastructure.services.youtube_vector_service import YouTubeVectorService

logger = Logger()

if __name__ == '__main__':
    knowledge_subject_name = "Dr Enéas"
    source_type = SourceType.YOUTUBE
    video_id = "8OQGUL9ZE0I"
    language = "pt"
    title = "Em palestra de 1999, Dr. Enéas explica por que acredita em Deus"

    pprint(settings.model_dump())

    wea_client = WeaviateClient(vector_config=settings.vector)

    ks_repository = KnowledgeSubjectSQLRepository()
    ks_service = KnowledgeSubjectService(ks_repository)

    knowledge_subject = ks_service.get_by_name(knowledge_subject_name)

    if knowledge_subject is None:
        knowledge_subject = ks_service.create_subject(name=knowledge_subject_name, external_ref="",
                                                      description="Acervo Dr Enéas")

    cs_repository = ContentSourceSQLRepository()
    cs_service = ContentSourceService(cs_repository)

    source = cs_service.get_by_source_info(source_type=source_type, external_source=video_id)

    if source:
        logger.info("Source already exists, skipping ingestion",
                    context={"source_type": source_type.value, "external_source": video_id})
        exit()

    source = cs_service.create_source(
        subject_id=knowledge_subject.id,
        source_type=source_type,
        external_source=video_id,
        title=title,
        language=language,
        status=ContentSourceStatus.PENDING
    )

    ingestion_repository = IngestionJobSQLRepository()
    ingestion_service = IngestionJobService(repository=ingestion_repository)

    model = settings.model_embedding.name
    model_loader = ModelLoaderService(model)
    embedding_service = EmbeddingService(model_loader)

    ingestion = ingestion_service.create_job(
        content_source_id=source.id,
        status=IngestionJobStatus.STARTED,
        embedding_model=model_loader.model_name,
        pipeline_version="1.0"
    )

    cs_service.update_processing_status(content_source_id=source.id, status=ContentSourceStatus.PROCESSING)

    yt_extractor = YoutubeExtractor(video_id=video_id)
    ytts = YoutubeDataProcessService(model_loader_service=model_loader, yt_extractor=yt_extractor)
    result: List[Document] = ytts.split_transcript(mode="tokens", tokens_per_chunk=512, tokens_overlap=30)

    ingestion_service.update_job(
        job_id=ingestion.id,
        status=IngestionJobStatus.PROCESSING
    )

    list_chunk: List[ChunkEntity] = []

    for doc in result:
        chunk_entity = ChunkEntity(
            id=uuid.uuid4(),
            job_id=uuid.uuid4(),
            content_source_id=source.id,
            source_type=SourceType(source.source_type),
            external_source=source.external_source,
            subject_id=knowledge_subject.id,
            content=doc.page_content,
            extra=doc.metadata,
            language=language,
            embedding_model=model_loader.model_name,
            created_at=datetime.now(timezone.utc),
            version_number=1
        )
        list_chunk.append(chunk_entity)

    chunk_repository = ChunkIndexSQLRepository()
    chunk_service = ChunkIndexService(chunk_repository)

    chunk_service.create_chunks(list_chunk)

    repository = ChunkWeaviateRepository(weaviate_client=wea_client, embedding_service=embedding_service,
                                         collection_name=settings.vector.weaviate_collection_name_chunks,
                                         text_key="content")

    service = YouTubeVectorService(repository=repository)

    created_ids = service.index_documents(list_chunk)

    cs_service.finish_ingestion(
        content_source_id=source.id,
        embedding_model=model_loader.model_name,
        dimensions=model_loader.dimensions,
        chunks=len(list_chunk)
    )

    ingestion_service.update_job(
        job_id=ingestion.id,
        status=IngestionJobStatus.FINISHED,
    )

    query_result: List[ChunkEntity] = service.search_by_video_id(video_id=video_id)

    query = service.search(query="livros", top_k=1)

    service.delete_by_video_id(video_id=video_id)
