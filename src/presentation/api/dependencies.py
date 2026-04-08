from typing import Any, Generator, Optional

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.application.ingestion_context import IngestionContext
from src.application.use_cases.auth_use_case import AuthUseCase
from src.application.use_cases.content_source_use_case import ContentSourceUseCase
from src.application.use_cases.delete_diarization_use_case import (
    DeleteDiarizationUseCase,
)
from src.application.use_cases.diarization_ingestion_use_case import (
    DiarizationIngestionUseCase,
)
from src.application.use_cases.file_ingestion_use_case import FileIngestionUseCase
from src.application.use_cases.generate_speaker_audio_access_url import (
    GenerateSpeakerAudioAccessUrlUseCase,
)
from src.application.use_cases.identify_speakers_in_processed_audio import (
    IdentifySpeakersInProcessedAudioUseCase,
)
from src.application.use_cases.knowledge_subject_use_case import KnowledgeSubjectUseCase
from src.application.use_cases.list_s3_audio_files import ListS3AudioFilesUseCase
from src.application.use_cases.manage_voice_profiles import (
    DeleteVoiceAudioFileUseCase,
    DeleteVoiceProfileUseCase,
    ListRegisteredVoiceProfilesUseCase,
    ListVoiceAudioFilesUseCase,
    RegisterNewVoiceProfileUseCase,
    TrainVoiceProfileFromSpeakerSegmentUseCase,
)
from src.application.use_cases.retrieve_processed_audio_history import (
    RetrieveProcessedAudioHistoryUseCase,
)
from src.application.use_cases.search_use_case import SearchUseCase
from src.application.use_cases.web_scraping_use_case import WebScrapingUseCase
from src.application.use_cases.youtube_ingestion_use_case import YoutubeIngestionUseCase
from src.config.settings import Settings

# Import services and repositories
from src.domain.entities.enums.vector_store_type_enum import VectorStoreType
from src.domain.interfaces.repository.retriver_repository import IVectorRepository
from src.domain.interfaces.services.i_event_bus import IEventBus
from src.domain.interfaces.services.i_task_queue import ITaskQueue
from src.infrastructure.connectors.connector_sql import Session as DBSessionFactory
from src.infrastructure.extractors.crawl4ai_extractor import Crawl4AIExtractor
from src.infrastructure.repositories.sql.chunk_duplicate_repository import (
    ChunkDuplicateSQLRepository,
)
from src.infrastructure.repositories.sql.chunk_index_repository import (
    ChunkIndexSQLRepository,
)
from src.infrastructure.repositories.sql.content_source_repository import (
    ContentSourceSQLRepository,
)
from src.infrastructure.repositories.sql.diarization_repository import (
    DiarizationRepository,
)
from src.infrastructure.repositories.sql.ingestion_job_repository import (
    IngestionJobSQLRepository,
)
from src.infrastructure.repositories.sql.knowledge_subject_repository import (
    KnowledgeSubjectSQLRepository,
)
from src.infrastructure.repositories.sql.user_repository import UserSQLRepository
from src.infrastructure.services.auth_service import AuthService
from src.infrastructure.services.chunk_duplicate_service import ChunkDuplicateService
from src.infrastructure.services.chunk_index_service import ChunkIndexService
from src.infrastructure.services.chunk_vector_service import ChunkVectorService
from src.infrastructure.services.content_source_service import ContentSourceService
from src.infrastructure.services.embedding_service import EmbeddingService
from src.infrastructure.services.ingestion_job_service import IngestionJobService
from src.infrastructure.services.knowledge_subject_service import (
    KnowledgeSubjectService,
)
from src.infrastructure.services.model_loader_service import ModelLoaderService
from src.infrastructure.services.re_rank_service import ReRankService
from src.infrastructure.services.youtube_vector_service import YouTubeVectorService


def get_db() -> Generator[Session, None, None]:
    db = DBSessionFactory()
    try:
        yield db
    finally:
        db.close()


def get_settings() -> Settings:
    from src.config.settings import settings

    return settings


# Repositories
def get_chunk_repo() -> ChunkIndexSQLRepository:
    return ChunkIndexSQLRepository()


def get_source_repo() -> ContentSourceSQLRepository:
    return ContentSourceSQLRepository()


def get_job_repo() -> IngestionJobSQLRepository:
    return IngestionJobSQLRepository()


def get_diarization_repo(db: Session = Depends(get_db)) -> DiarizationRepository:
    from src.infrastructure.repositories.sql.diarization_repository import (
        DiarizationRepository,
    )

    return DiarizationRepository(db)


def get_subject_repo() -> KnowledgeSubjectSQLRepository:
    return KnowledgeSubjectSQLRepository()


def get_user_repo() -> UserSQLRepository:
    return UserSQLRepository()


def get_duplicate_repo() -> ChunkDuplicateSQLRepository:
    return ChunkDuplicateSQLRepository()


# Services
def get_model_loader(request: Request) -> ModelLoaderService:
    return request.app.state.model_loader


def get_embedding_service(
    model_loader: Optional[ModelLoaderService] = Depends(get_model_loader),
) -> EmbeddingService:
    if model_loader is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail="Embedding model is not loaded or failed to initialize. Please check server logs.",
        )
    return EmbeddingService(model_loader_service=model_loader)


def get_auth_service() -> AuthService:
    return AuthService()


def get_weaviate_client(settings: Settings = Depends(get_settings)) -> Any:
    from src.infrastructure.repositories.vector.weaviate.weaviate_client import (
        WeaviateClient,
    )

    return WeaviateClient(settings.vector)


class _NotReadyVectorStore(IVectorRepository):
    """Dummy vector store returned when model loader is not yet initialized."""

    def retriever(self, *args, **kwargs):
        return []

    def create_documents(self, *args, **kwargs):
        return []

    def delete(self, *args, **kwargs):
        return 0

    def list_chunks(self, *args, **kwargs):
        return []

    def is_ready(self):
        return False


def get_vector_repository(
    settings: Settings = Depends(get_settings),
    model_loader: Optional[ModelLoaderService] = Depends(get_model_loader),
) -> IVectorRepository:
    if model_loader is None:
        return _NotReadyVectorStore()

    emb_service = EmbeddingService(model_loader_service=model_loader)
    # Automatically append dimensionality to collection/index name to avoid mismatches
    base_name = settings.vector.collection_name_chunks
    dimensions = model_loader.dimensions
    collection_name = f"{base_name}_{dimensions}"

    try:
        if settings.vector.store_type == VectorStoreType.CHROMA:
            from src.infrastructure.repositories.vector.chroma.chunk_repository import (
                ChunkChromaRepository,
            )

            return ChunkChromaRepository(
                embedding_service=emb_service,
                host=settings.vector.chroma_host,
                port=settings.vector.chroma_port,
                collection_name=collection_name,
            )

        if settings.vector.store_type == VectorStoreType.WEAVIATE:
            from src.infrastructure.repositories.vector.weaviate.chunk_repository import (
                ChunkWeaviateRepository,
            )
            from src.infrastructure.repositories.vector.weaviate.weaviate_client import (
                WeaviateClient,
            )

            client = WeaviateClient(settings.vector)
            return ChunkWeaviateRepository(
                weaviate_client=client,
                embedding_service=emb_service,
                collection_name=collection_name,
            )

        if settings.vector.store_type == VectorStoreType.FAISS:
            from src.infrastructure.repositories.vector.faiss.chunk_repository import (
                ChunkFAISSRepository,
            )

            return ChunkFAISSRepository(
                embedding_service=emb_service,
                index_path=settings.vector.vector_index_path,
                index_name=collection_name,
            )

        if settings.vector.store_type == VectorStoreType.QDRANT:
            from src.infrastructure.repositories.vector.qdrant.chunk_repository import (
                ChunkQdrantRepository,
            )
            from src.infrastructure.repositories.vector.qdrant.connector import (
                QdrantConnector,
            )

            connector = QdrantConnector(
                host=settings.vector.qdrant_host,
                port=settings.vector.qdrant_port,
                grpc_port=settings.vector.qdrant_grpc_port,
                api_key=settings.vector.qdrant_api_key,
            )
            return ChunkQdrantRepository(
                connector=connector,
                embedding_service=emb_service,
                collection_name=collection_name,
            )
    except ImportError as e:
        from fastapi import HTTPException

        error_msg = (
            f"Vector driver for {settings.vector.store_type} is not installed: {e}. "
            f"Please run 'pip install qdrant-client' (or the appropriate driver)."
        )
        from src.config.logger import Logger

        Logger().error(error_msg, context={"store_type": settings.vector.store_type})
        raise HTTPException(status_code=500, detail=error_msg)

    raise ValueError(f"Unsupported vector store type: {settings.vector.store_type}")


def get_ks_service(
    repo: KnowledgeSubjectSQLRepository = Depends(get_subject_repo),
) -> KnowledgeSubjectService:
    return KnowledgeSubjectService(repo)


def get_cs_service(
    repo: ContentSourceSQLRepository = Depends(get_source_repo),
) -> ContentSourceService:
    return ContentSourceService(repo)


def get_job_service(
    repo: IngestionJobSQLRepository = Depends(get_job_repo),
) -> IngestionJobService:
    return IngestionJobService(repo)


def get_rerank_service(request: Request) -> ReRankService:
    return request.app.state.rerank_service


def get_task_queue_service(request: Request) -> ITaskQueue:
    return request.app.state.task_queue


def get_event_bus(request: Request) -> IEventBus:
    return request.app.state.event_bus


def get_chunk_vector_service(
    vector_repo: IVectorRepository = Depends(get_vector_repository),
    rerank_service: ReRankService = Depends(get_rerank_service),
) -> ChunkVectorService:
    return ChunkVectorService(vector_repo, rerank_service=rerank_service)


def get_chunk_index_service(
    repo: ChunkIndexSQLRepository = Depends(get_chunk_repo),
) -> ChunkIndexService:
    return ChunkIndexService(repo)


def get_duplicate_service(
    repo: ChunkDuplicateSQLRepository = Depends(get_duplicate_repo),
    chunk_repo: ChunkIndexSQLRepository = Depends(get_chunk_repo),
    vector_service: ChunkVectorService = Depends(get_chunk_vector_service),
) -> ChunkDuplicateService:
    return ChunkDuplicateService(repo, chunk_repo, vector_service)


def get_youtube_vector_service(
    vector_repo: IVectorRepository = Depends(get_vector_repository),
) -> YouTubeVectorService:
    return YouTubeVectorService(vector_repo)


# Use Cases
def get_search_chunks_use_case(
    vector_svc: ChunkVectorService = Depends(get_chunk_vector_service),
    ks_svc: KnowledgeSubjectService = Depends(get_ks_service),
) -> SearchUseCase:
    return SearchUseCase(vector_service=vector_svc, ks_service=ks_svc)


def get_auth_use_case(
    user_repo: UserSQLRepository = Depends(get_user_repo),
    auth_svc: AuthService = Depends(get_auth_service),
) -> AuthUseCase:
    return AuthUseCase(user_repo=user_repo, auth_service=auth_svc)


def get_current_user(
    request: Request,
    auth_use_case: AuthUseCase = Depends(get_auth_use_case),
    settings: Settings = Depends(get_settings),
):
    """Dependency that returns the current authenticated user.
    If Google SSO is disabled, it returns a mock admin user."""
    if not settings.auth.enable_google:
        # Return a mock user for open access
        from src.domain.entities.user import User

        return User(id="admin", email="admin@whatyousaid.local", full_name="Admin")

    # If enabled, logic to check header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Authentication required")

    token = auth_header.split(" ")[1]
    user = auth_use_case.verify_session(token)
    if not user:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="Invalid session")

    return user


def get_ingest_youtube_use_case(
    ks_svc: KnowledgeSubjectService = Depends(get_ks_service),
    cs_svc: ContentSourceService = Depends(get_cs_service),
    job_svc: IngestionJobService = Depends(get_job_service),
    model_loader: ModelLoaderService = Depends(get_model_loader),
    embed_svc: EmbeddingService = Depends(get_embedding_service),
    chunk_svc: ChunkIndexService = Depends(get_chunk_index_service),
    yt_vector_svc: YouTubeVectorService = Depends(get_youtube_vector_service),
    event_bus: IEventBus = Depends(get_event_bus),
    settings: Settings = Depends(get_settings),
) -> YoutubeIngestionUseCase:
    return YoutubeIngestionUseCase(
        ks_service=ks_svc,
        cs_service=cs_svc,
        ingestion_service=job_svc,
        model_loader_service=model_loader,
        embedding_service=embed_svc,
        chunk_service=chunk_svc,
        vector_service=yt_vector_svc,
        vector_store_type=settings.vector.store_type.value,
        event_bus=event_bus,
    )


def get_content_source_use_case(
    cs_svc: ContentSourceService = Depends(get_cs_service),
    chunk_svc: ChunkIndexService = Depends(get_chunk_index_service),
    vector_repo: IVectorRepository = Depends(get_vector_repository),
) -> ContentSourceUseCase:
    return ContentSourceUseCase(
        cs_service=cs_svc,
        chunk_service=chunk_svc,
        vector_repo=vector_repo,
    )


def get_ks_use_case(
    ks_svc: KnowledgeSubjectService = Depends(get_ks_service),
    cs_use_case: ContentSourceUseCase = Depends(get_content_source_use_case),
    vector_repo: IVectorRepository = Depends(get_vector_repository),
) -> KnowledgeSubjectUseCase:
    return KnowledgeSubjectUseCase(
        ks_service=ks_svc,
        cs_use_case=cs_use_case,
        vector_repo=vector_repo,
    )


def get_file_ingestion_use_case(
    ks_svc: KnowledgeSubjectService = Depends(get_ks_service),
    cs_svc: ContentSourceService = Depends(get_cs_service),
    job_svc: IngestionJobService = Depends(get_job_service),
    model_loader: ModelLoaderService = Depends(get_model_loader),
    embed_svc: EmbeddingService = Depends(get_embedding_service),
    chunk_svc: ChunkIndexService = Depends(get_chunk_index_service),
    vector_svc: ChunkVectorService = Depends(get_chunk_vector_service),
    event_bus: IEventBus = Depends(get_event_bus),
    settings: Settings = Depends(get_settings),
) -> FileIngestionUseCase:
    return FileIngestionUseCase(
        ks_service=ks_svc,
        cs_service=cs_svc,
        ingestion_service=job_svc,
        model_loader_service=model_loader,
        embedding_service=embed_svc,
        chunk_service=chunk_svc,
        vector_service=vector_svc,
        vector_store_type=settings.vector.store_type.value,
        event_bus=event_bus,
    )


def get_web_extractor() -> Crawl4AIExtractor:
    return Crawl4AIExtractor()


def get_web_scraping_use_case(
    ks_svc: KnowledgeSubjectService = Depends(get_ks_service),
    cs_svc: ContentSourceService = Depends(get_cs_service),
    job_svc: IngestionJobService = Depends(get_job_service),
    model_loader: ModelLoaderService = Depends(get_model_loader),
    embed_svc: EmbeddingService = Depends(get_embedding_service),
    chunk_svc: ChunkIndexService = Depends(get_chunk_index_service),
    vector_svc: ChunkVectorService = Depends(get_chunk_vector_service),
    event_bus: IEventBus = Depends(get_event_bus),
    settings: Settings = Depends(get_settings),
    extractor: Crawl4AIExtractor = Depends(get_web_extractor),
) -> WebScrapingUseCase:
    return WebScrapingUseCase(
        ks_service=ks_svc,
        cs_service=cs_svc,
        ingestion_service=job_svc,
        model_loader_service=model_loader,
        embedding_service=embed_svc,
        chunk_service=chunk_svc,
        vector_service=vector_svc,
        vector_store_type=settings.vector.store_type.value,
        event_bus=event_bus,
        extractor=extractor,
    )


def get_diarization_ingestion_use_case(
    db: Session = Depends(get_db),
    ks_svc: KnowledgeSubjectService = Depends(get_ks_service),
    cs_svc: ContentSourceService = Depends(get_cs_service),
    job_svc: IngestionJobService = Depends(get_job_service),
    model_loader: ModelLoaderService = Depends(get_model_loader),
    embed_svc: EmbeddingService = Depends(get_embedding_service),
    chunk_svc: ChunkIndexService = Depends(get_chunk_index_service),
    vector_svc: ChunkVectorService = Depends(get_chunk_vector_service),
    event_bus: IEventBus = Depends(get_event_bus),
    settings: Settings = Depends(get_settings),
) -> DiarizationIngestionUseCase:
    from src.infrastructure.repositories.sql.diarization_repository import (
        DiarizationRepository,
    )

    return DiarizationIngestionUseCase(
        diarization_repo=DiarizationRepository(db),
        ks_service=ks_svc,
        cs_service=cs_svc,
        ingestion_service=job_svc,
        model_loader_service=model_loader,
        embedding_service=embed_svc,
        chunk_service=chunk_svc,
        vector_service=vector_svc,
        vector_store_type=settings.vector.store_type.value,
        event_bus=event_bus,
    )


def get_identify_speakers_use_case(
    db: Session = Depends(get_db),
) -> IdentifySpeakersInProcessedAudioUseCase:
    return IdentifySpeakersInProcessedAudioUseCase(db)


def get_retrieve_history_use_case(
    db: Session = Depends(get_db),
) -> RetrieveProcessedAudioHistoryUseCase:
    return RetrieveProcessedAudioHistoryUseCase(db)


def get_list_s3_files_use_case(
    db: Session = Depends(get_db),
) -> ListS3AudioFilesUseCase:
    return ListS3AudioFilesUseCase(db)


def get_delete_diarization_use_case(
    db: Session = Depends(get_db),
    cs_svc: ContentSourceService = Depends(get_cs_service),
) -> DeleteDiarizationUseCase:
    return DeleteDiarizationUseCase(db, cs_service=cs_svc)


def get_generate_speaker_url_use_case(
    db: Session = Depends(get_db),
) -> GenerateSpeakerAudioAccessUrlUseCase:
    return GenerateSpeakerAudioAccessUrlUseCase(db)


def get_register_voice_profile_use_case(
    db: Session = Depends(get_db),
) -> RegisterNewVoiceProfileUseCase:
    return RegisterNewVoiceProfileUseCase(db)


def get_train_voice_from_speaker_use_case(
    db: Session = Depends(get_db),
) -> TrainVoiceProfileFromSpeakerSegmentUseCase:
    return TrainVoiceProfileFromSpeakerSegmentUseCase(db)


def get_list_voice_profiles_use_case(
    db: Session = Depends(get_db),
) -> ListRegisteredVoiceProfilesUseCase:
    return ListRegisteredVoiceProfilesUseCase(db)


def get_delete_voice_profile_use_case(
    db: Session = Depends(get_db),
) -> DeleteVoiceProfileUseCase:
    return DeleteVoiceProfileUseCase(db)


def get_list_voice_audio_files_use_case(
    db: Session = Depends(get_db),
) -> ListVoiceAudioFilesUseCase:
    return ListVoiceAudioFilesUseCase(db)


def get_delete_voice_audio_file_use_case(
    db: Session = Depends(get_db),
) -> DeleteVoiceAudioFileUseCase:
    return DeleteVoiceAudioFileUseCase(db)


# --- Worker context resolution (no HTTP Request required) ---


def resolve_ingestion_context(app) -> IngestionContext:
    """Resolve common ingestion dependencies from app state without an HTTP Request.

    Used by background workers to avoid unittest.mock in production code.
    """
    s = get_settings()
    model_loader = app.state.model_loader
    return IngestionContext(
        settings=s,
        ks_service=get_ks_service(repo=get_subject_repo()),
        cs_service=get_cs_service(repo=get_source_repo()),
        job_service=get_job_service(repo=get_job_repo()),
        model_loader=model_loader,
        embed_service=get_embedding_service(model_loader=model_loader),
        chunk_service=get_chunk_index_service(repo=get_chunk_repo()),
        event_bus=app.state.event_bus,
        vector_store_type=s.vector.store_type.value,
    )


def resolve_vector_repository(app) -> IVectorRepository:
    """Resolve vector repository from app state without an HTTP Request."""
    s = get_settings()
    model_loader = app.state.model_loader
    return get_vector_repository(settings=s, model_loader=model_loader)


def resolve_rerank_service(app) -> "ReRankService":
    """Resolve rerank service from app state without an HTTP Request."""
    return app.state.rerank_service
