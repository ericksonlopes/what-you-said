import logging
from typing import Any
from src.application.dtos.commands.ingest_file_command import IngestFileCommand
from src.application.dtos.commands.ingest_youtube_command import IngestYoutubeCommand
from src.application.service_registry import registry

logger = logging.getLogger(__name__)


def run_file_ingestion_worker(cmd: IngestFileCommand):
    """Picklable worker function for file ingestion."""
    # We need a dummy request or a way to get the app state
    app = registry.get("app")
    if not app:
        logger.error("ServiceRegistry: 'app' not registered. Cannot run worker.")
        return

    # Manually resolve the use case using the same logic as dependencies.py
    # but without needing a Request object if possible, or mocking it.
    from unittest.mock import MagicMock

    mock_request = MagicMock()
    mock_request.app = app

    # dependencies.py functions often take 'request: Request'
    # Let's see if we can resolve it manually to avoid complex dependency chains
    try:
        from src.presentation.api import dependencies as deps

        settings = deps.get_settings()
        ks_svc = deps.get_ks_service(repo=deps.get_subject_repo())
        cs_svc = deps.get_cs_service(repo=deps.get_source_repo())
        job_svc = deps.get_job_service(repo=deps.get_job_repo())
        model_loader = deps.get_model_loader(mock_request)
        embed_svc = deps.get_embedding_service(model_loader=model_loader)
        chunk_svc = deps.get_chunk_index_service(repo=deps.get_chunk_repo())

        # Intermediate dependencies
        vector_repo = deps.get_vector_repository(
            settings=settings, model_loader=model_loader
        )
        rerank_svc = deps.get_rerank_service(request=mock_request)
        vector_svc = deps.get_chunk_vector_service(
            vector_repo=vector_repo, rerank_service=rerank_svc
        )
        event_bus = deps.get_event_bus(request=mock_request)

        from src.application.use_cases.file_ingestion_use_case import (
            FileIngestionUseCase,
        )

        use_case = FileIngestionUseCase(
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

        use_case.execute(cmd)
    except Exception as e:
        logger.error(
            f"Worker Error: Failed to execute file ingestion: {e}", exc_info=True
        )


def run_youtube_ingestion_worker(cmd: IngestYoutubeCommand):
    """Picklable worker function for YouTube ingestion."""
    from src.application.service_registry import registry

    app = registry.get("app")
    if not app:
        return

    from unittest.mock import MagicMock

    mock_request = MagicMock()
    mock_request.app = app

    try:
        from src.presentation.api import dependencies as deps

        settings = deps.get_settings()
        ks_svc = deps.get_ks_service(repo=deps.get_subject_repo())
        cs_svc = deps.get_cs_service(repo=deps.get_source_repo())
        job_svc = deps.get_job_service(repo=deps.get_job_repo())
        model_loader = deps.get_model_loader(mock_request)
        embed_svc = deps.get_embedding_service(model_loader=model_loader)
        chunk_svc = deps.get_chunk_index_service(repo=deps.get_chunk_repo())

        # Intermediate dependencies
        vector_repo = deps.get_vector_repository(
            settings=settings, model_loader=model_loader
        )
        vector_svc = deps.get_youtube_vector_service(vector_repo=vector_repo)
        event_bus = deps.get_event_bus(request=mock_request)

        from src.application.use_cases.youtube_ingestion_use_case import (
            YoutubeIngestionUseCase,
        )

        use_case = YoutubeIngestionUseCase(
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

        use_case.execute(cmd)
    except Exception as e:
        logger.error(
            f"Worker Error: Failed to execute YouTube ingestion: {e}", exc_info=True
        )


def run_web_ingestion_worker(cmd: Any):
    """Picklable worker function for Web Scraping ingestion."""
    import asyncio
    from src.application.service_registry import registry

    app = registry.get("app")
    if not app:
        return

    from unittest.mock import MagicMock

    mock_request = MagicMock()
    mock_request.app = app

    async def _run():
        try:
            from src.presentation.api import dependencies as deps

            settings = deps.get_settings()
            ks_svc = deps.get_ks_service(repo=deps.get_subject_repo())
            cs_svc = deps.get_cs_service(repo=deps.get_source_repo())
            job_svc = deps.get_job_service(repo=deps.get_job_repo())
            model_loader = deps.get_model_loader(mock_request)
            embed_svc = deps.get_embedding_service(model_loader=model_loader)
            chunk_svc = deps.get_chunk_index_service(repo=deps.get_chunk_repo())

            vector_repo = deps.get_vector_repository(
                settings=settings, model_loader=model_loader
            )
            rerank_svc = deps.get_rerank_service(request=mock_request)
            vector_svc = deps.get_chunk_vector_service(
                vector_repo=vector_repo, rerank_service=rerank_svc
            )
            event_bus = deps.get_event_bus(request=mock_request)
            extractor = deps.get_web_extractor()

            from src.application.use_cases.web_scraping_use_case import (
                WebScrapingUseCase,
            )

            use_case = WebScrapingUseCase(
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

            await use_case.execute(cmd)
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                f"Worker Error: Failed to execute Web Scraping: {e}", exc_info=True
            )

    asyncio.run(_run())
