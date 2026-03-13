from pprint import pprint

from src.application.dtos.enums.youtube_data_type import YoutubeDataType
from src.config.logger import Logger
from src.config.settings import settings
from src.domain.entities.enums.source_type_enum_entity import SourceType
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
from src.infrastructure.services.youtube_vector_service import YouTubeVectorService

logger = Logger()

if __name__ == '__main__':
    knowledge_subject_name = "Dr Enéas"
    source_type = SourceType.YOUTUBE
    video_id = "8OQGUL9ZE0I"
    youtube_data_type = YoutubeDataType.VIDEO
    language = "pt"
    title = "Em palestra de 1999, Dr. Enéas explica por que acredita em Deus"

    pprint(settings.model_dump())

    wea_client = WeaviateClient(vector_config=settings.vector)

    ks_repository = KnowledgeSubjectSQLRepository()
    ks_service = KnowledgeSubjectService(ks_repository)

    cs_repository = ContentSourceSQLRepository()
    cs_service = ContentSourceService(cs_repository)

    ingestion_repository = IngestionJobSQLRepository()
    ingestion_service = IngestionJobService(repository=ingestion_repository)

    model = settings.model_embedding.name
    model_loader = ModelLoaderService(model)
    embedding_service = EmbeddingService(model_loader)

    chunk_repository = ChunkIndexSQLRepository()
    chunk_service = ChunkIndexService(chunk_repository)

    repository = ChunkWeaviateRepository(weaviate_client=wea_client, embedding_service=embedding_service,
                                         collection_name=settings.vector.weaviate_collection_name_chunks,
                                         text_key="content")

    vector_service = YouTubeVectorService(repository=repository)

    # Application use case
    from src.application.dtos.commands.ingest_youtube_command import IngestYoutubeCommand
    from src.application.use_cases.ingest_youtube_use_case import IngestYoutubeUseCase

    ks_service.create_subject(name=knowledge_subject_name, description="Conhecimento sobre Dr Enéas")

    use_case = IngestYoutubeUseCase(
        ks_service=ks_service,
        cs_service=cs_service,
        ingestion_service=ingestion_service,
        model_loader_service=model_loader,
        embedding_service=embedding_service,
        chunk_service=chunk_service,
        vector_service=vector_service,
    )

    cmd = IngestYoutubeCommand(
        video_url=video_id,
        title=title,
        subject_name=knowledge_subject_name,
        data_type=youtube_data_type,
        language=language,
        tokens_per_chunk=512,
        tokens_overlap=30,
    )

    result = use_case.execute(cmd)
    pprint({"ingest_result": result})
