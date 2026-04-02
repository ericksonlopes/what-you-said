import logging
from typing import Any

from src.application.dtos.commands.ingest_file_command import IngestFileCommand
from src.application.dtos.commands.ingest_youtube_command import IngestYoutubeCommand
from src.application.service_registry import registry
from src.infrastructure.loggers.std_logger import (
    set_global_context,
    clear_global_context,
)

logger = logging.getLogger(__name__)


def _get_app():
    """Retrieve the app instance from the service registry."""
    app = registry.get("app")
    if not app:
        logger.error("ServiceRegistry: 'app' not registered. Cannot run worker.")
    return app


def _get_correlation_id(cmd: Any, fallback: str) -> str:
    """Extract correlation ID from a command object."""
    jid = getattr(cmd, "ingestion_job_id", None)
    return str(jid) if jid else fallback


def run_file_ingestion_worker(cmd: IngestFileCommand):
    """Background worker function for file ingestion."""
    set_global_context(
        {"correlation_id": _get_correlation_id(cmd, "worker-file")}
    )

    app = _get_app()
    if not app:
        clear_global_context()
        return

    try:
        from src.presentation.api.dependencies import (
            resolve_ingestion_context,
            resolve_vector_repository,
            resolve_rerank_service,
        )
        from src.infrastructure.services.chunk_vector_service import ChunkVectorService
        from src.application.use_cases.file_ingestion_use_case import (
            FileIngestionUseCase,
        )

        ctx = resolve_ingestion_context(app)
        vector_repo = resolve_vector_repository(app)
        rerank_svc = resolve_rerank_service(app)
        vector_svc = ChunkVectorService(vector_repo, rerank_service=rerank_svc)

        use_case = FileIngestionUseCase(
            ks_service=ctx.ks_service,
            cs_service=ctx.cs_service,
            ingestion_service=ctx.job_service,
            model_loader_service=ctx.model_loader,
            embedding_service=ctx.embed_service,
            chunk_service=ctx.chunk_service,
            vector_service=vector_svc,
            vector_store_type=ctx.vector_store_type,
            event_bus=ctx.event_bus,
        )

        use_case.execute(cmd)
    except Exception as e:
        logger.error(
            f"Worker Error: Failed to execute file ingestion: {e}", exc_info=True
        )
    finally:
        clear_global_context()


def run_youtube_ingestion_worker(cmd: IngestYoutubeCommand):
    """Background worker function for YouTube ingestion."""
    set_global_context(
        {"correlation_id": _get_correlation_id(cmd, "worker-youtube")}
    )

    app = _get_app()
    if not app:
        clear_global_context()
        return

    try:
        from src.presentation.api.dependencies import (
            resolve_ingestion_context,
            resolve_vector_repository,
        )
        from src.infrastructure.services.youtube_vector_service import (
            YouTubeVectorService,
        )
        from src.application.use_cases.youtube_ingestion_use_case import (
            YoutubeIngestionUseCase,
        )

        ctx = resolve_ingestion_context(app)
        vector_repo = resolve_vector_repository(app)
        vector_svc = YouTubeVectorService(vector_repo)

        use_case = YoutubeIngestionUseCase(
            ks_service=ctx.ks_service,
            cs_service=ctx.cs_service,
            ingestion_service=ctx.job_service,
            model_loader_service=ctx.model_loader,
            embedding_service=ctx.embed_service,
            chunk_service=ctx.chunk_service,
            vector_service=vector_svc,
            vector_store_type=ctx.vector_store_type,
            event_bus=ctx.event_bus,
        )

        use_case.execute(cmd)
    except Exception as e:
        logger.error(
            f"Worker Error: Failed to execute YouTube ingestion: {e}", exc_info=True
        )
    finally:
        clear_global_context()


def run_web_ingestion_worker(cmd: Any):
    """Background worker function for Web Scraping ingestion."""
    set_global_context(
        {"correlation_id": _get_correlation_id(cmd, "worker-web")}
    )

    import asyncio

    app = _get_app()
    if not app:
        clear_global_context()
        return

    async def _run():
        try:
            from src.presentation.api.dependencies import (
                resolve_ingestion_context,
                resolve_vector_repository,
                resolve_rerank_service,
                get_web_extractor,
            )
            from src.infrastructure.services.chunk_vector_service import (
                ChunkVectorService,
            )
            from src.application.use_cases.web_scraping_use_case import (
                WebScrapingUseCase,
            )

            ctx = resolve_ingestion_context(app)
            vector_repo = resolve_vector_repository(app)
            rerank_svc = resolve_rerank_service(app)
            vector_svc = ChunkVectorService(vector_repo, rerank_service=rerank_svc)
            extractor = get_web_extractor()

            use_case = WebScrapingUseCase(
                ks_service=ctx.ks_service,
                cs_service=ctx.cs_service,
                ingestion_service=ctx.job_service,
                model_loader_service=ctx.model_loader,
                embedding_service=ctx.embed_service,
                chunk_service=ctx.chunk_service,
                vector_service=vector_svc,
                vector_store_type=ctx.vector_store_type,
                event_bus=ctx.event_bus,
                extractor=extractor,
            )

            await use_case.execute(cmd)
        except Exception as e:
            logging.getLogger(__name__).error(
                f"Worker Error: Failed to execute Web Scraping: {e}", exc_info=True
            )
        finally:
            clear_global_context()

    asyncio.run(_run())
