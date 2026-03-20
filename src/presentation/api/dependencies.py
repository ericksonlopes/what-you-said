from typing import Any

from fastapi import Depends, Request

from src.application.use_cases.content_source_use_case import ContentSourceUseCase
from src.application.use_cases.file_ingestion_use_case import FileIngestionUseCase
from src.application.use_cases.knowledge_subject_use_case import KnowledgeSubjectUseCase
from src.application.use_cases.search_use_case import SearchUseCase
from src.application.use_cases.youtube_ingestion_use_case import YoutubeIngestionUseCase
from src.config.settings import Settings

# Import services and repositories
from src.domain.entities.enums.vector_store_type_enum import VectorStoreType
from src.domain.interfaces.repository.retriver_repository import IVectorRepository
from src.infrastructure.repositories.sql.chunk_index_repository import (
    ChunkIndexSQLRepository,
)
from src.infrastructure.repositories.sql.content_source_repository import (
    ContentSourceSQLRepository,
)
from src.infrastructure.repositories.sql.ingestion_job_repository import (
    IngestionJobSQLRepository,
)
from src.infrastructure.repositories.sql.knowledge_subject_repository import (
    KnowledgeSubjectSQLRepository,
)
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


# This module acts as the DI container for the FastAPI app.
# Each function provides an instance of a domain service or use case.


def get_settings() -> Settings:
    return Settings()


# Repositories
def get_chunk_repo() -> ChunkIndexSQLRepository:
    return ChunkIndexSQLRepository()


def get_source_repo() -> ContentSourceSQLRepository:
    return ContentSourceSQLRepository()


def get_job_repo() -> IngestionJobSQLRepository:
    return IngestionJobSQLRepository()


def get_subject_repo() -> KnowledgeSubjectSQLRepository:
    return KnowledgeSubjectSQLRepository()


# Services
def get_model_loader(request: Request) -> ModelLoaderService:
    return request.app.state.model_loader


def get_embedding_service(
    model_loader: ModelLoaderService = Depends(get_model_loader),
) -> EmbeddingService:
    return EmbeddingService(model_loader_service=model_loader)


def get_weaviate_client(settings: Settings = Depends(get_settings)) -> Any:
    from src.infrastructure.repositories.vector.weaviate.weaviate_client import (
        WeaviateClient,
    )

    return WeaviateClient(settings.vector)


def get_vector_repository(
    settings: Settings = Depends(get_settings),
    model_loader: ModelLoaderService = Depends(get_model_loader),
) -> IVectorRepository:
    emb_service = EmbeddingService(model_loader_service=model_loader)
    # Automatically append dimensionality to collection/index name to avoid mismatches
    base_name = settings.vector.collection_name_chunks
    dimensions = model_loader.dimensions
    collection_name = f"{base_name}_{dimensions}"

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


def get_chunk_vector_service(
    vector_repo: IVectorRepository = Depends(get_vector_repository),
    rerank_service: ReRankService = Depends(get_rerank_service),
) -> ChunkVectorService:
    return ChunkVectorService(vector_repo, rerank_service=rerank_service)


def get_chunk_index_service(
    repo: ChunkIndexSQLRepository = Depends(get_chunk_repo),
) -> ChunkIndexService:
    return ChunkIndexService(repo)


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


def get_ingest_youtube_use_case(
    ks_svc: KnowledgeSubjectService = Depends(get_ks_service),
    cs_svc: ContentSourceService = Depends(get_cs_service),
    job_svc: IngestionJobService = Depends(get_job_service),
    model_loader: ModelLoaderService = Depends(get_model_loader),
    embed_svc: EmbeddingService = Depends(get_embedding_service),
    chunk_svc: ChunkIndexService = Depends(get_chunk_index_service),
    yt_vector_svc: YouTubeVectorService = Depends(get_youtube_vector_service),
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
    )
