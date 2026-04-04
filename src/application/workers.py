import logging
from typing import Any

from src.application.dtos.commands.ingest_diarization_command import (
    IngestDiarizationCommand,
)
from src.application.dtos.commands.ingest_file_command import IngestFileCommand
from src.application.dtos.commands.ingest_web_command import IngestWebCommand
from src.application.dtos.commands.ingest_youtube_command import IngestYoutubeCommand
from src.application.dtos.commands.process_audio_command import ProcessAudioCommand
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
    set_global_context({"correlation_id": _get_correlation_id(cmd, "worker-file")})

    if isinstance(cmd, dict):
        cmd = IngestFileCommand(**cmd)

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
    set_global_context({"correlation_id": _get_correlation_id(cmd, "worker-youtube")})

    if isinstance(cmd, dict):
        cmd = IngestYoutubeCommand(**cmd)

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


def run_diarization_ingestion_worker(cmd: IngestDiarizationCommand):
    """Background worker function for direct diarization ingestion."""
    set_global_context(
        {"correlation_id": _get_correlation_id(cmd, "worker-diarization")}
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
        from src.infrastructure.repositories.sql.diarization_repository import (
            DiarizationRepository,
        )
        from src.application.use_cases.diarization_ingestion_use_case import (
            DiarizationIngestionUseCase,
        )

        ctx = resolve_ingestion_context(app)
        vector_repo = resolve_vector_repository(app)
        rerank_svc = resolve_rerank_service(app)
        vector_svc = ChunkVectorService(vector_repo, rerank_service=rerank_svc)

        # DiarizationRepository needs a DB session
        from src.infrastructure.repositories.sql.connector import Session as DBSession

        db = DBSession()
        try:
            diarization_repo = DiarizationRepository(db)
            use_case = DiarizationIngestionUseCase(
                diarization_repo=diarization_repo,
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
        finally:
            db.close()
    except Exception as e:
        logger.error(
            f"Worker Error: Failed to execute diarization ingestion: {e}", exc_info=True
        )
    finally:
        clear_global_context()


def run_web_ingestion_worker(cmd: Any):
    """Background worker function for Web Scraping ingestion."""
    set_global_context({"correlation_id": _get_correlation_id(cmd, "worker-web")})

    if isinstance(cmd, dict):
        cmd = IngestWebCommand(**cmd)

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


def _audio_diarization_subprocess(cmd_dict: dict):
    """Run audio diarization in a separate process to avoid torch/CUDA thread deadlocks."""
    from src.infrastructure.repositories.sql.connector import (
        Session as DBSessionFactory,
    )
    from src.application.use_cases.process_audio_diarization_pipeline import (
        ProcessAudioDiarizationPipelineUseCase,
    )
    from src.infrastructure.repositories.sql.diarization_repository import (
        DiarizationRepository,
    )
    from src.infrastructure.services.redis_event_bus import RedisEventBus

    db = DBSessionFactory()
    event_bus = RedisEventBus()
    diarization_id = cmd_dict.get("diarization_id")
    try:
        use_case = ProcessAudioDiarizationPipelineUseCase(db, event_bus=event_bus)
        use_case.execute(
            source_type=cmd_dict["source_type"],
            source=cmd_dict["source"],
            language=cmd_dict["language"],
            num_speakers=cmd_dict["num_speakers"],
            min_speakers=cmd_dict["min_speakers"],
            max_speakers=cmd_dict["max_speakers"],
            model_size=cmd_dict["model_size"],
            recognize_voices=cmd_dict["recognize_voices"],
            diarization_id=diarization_id,
        )
    except Exception as e:
        logger.error("Audio diarization failed: %s", e, exc_info=True)
        if diarization_id:
            repo = DiarizationRepository(db)
            from src.domain.entities.enums.diarization_status_enum import (
                DiarizationStatus,
            )

            repo.update_status(
                diarization_id,
                DiarizationStatus.FAILED.value,
                error_message=str(e),
                status_message="Falha no processamento",
            )
            event_bus.publish(
                "ingestion_status",
                {
                    "type": "diarization",
                    "id": diarization_id,
                    "status": DiarizationStatus.FAILED.value,
                    "message": f"Erro na diarização: {str(e)}",
                },
            )
        raise
    finally:
        db.close()


def run_audio_diarization_worker(cmd: ProcessAudioCommand):
    """Background worker function for audio diarization and recognition.

    Spawns a separate process because whisperx/torch models can deadlock
    when run inside daemon threads (Redis worker threads).
    """
    import multiprocessing
    from dataclasses import asdict

    set_global_context({"correlation_id": f"worker-audio-{cmd.source_type}"})

    try:
        cmd_dict = asdict(cmd)
        logger.info("Spawning audio diarization subprocess for source=%s", cmd.source)

        ctx = multiprocessing.get_context("spawn")
        process = ctx.Process(target=_audio_diarization_subprocess, args=(cmd_dict,))
        process.start()
        process.join()

        if process.exitcode != 0:
            logger.error(
                "Audio diarization subprocess exited with code %d", process.exitcode
            )
            if cmd.diarization_id:
                from src.infrastructure.repositories.sql.connector import (
                    Session as DBSessionFactory,
                )
                from src.infrastructure.repositories.sql.diarization_repository import (
                    DiarizationRepository,
                )
                from src.infrastructure.services.redis_event_bus import RedisEventBus

                db = DBSessionFactory()
                try:
                    repo = DiarizationRepository(db)
                    from src.domain.entities.enums.diarization_status_enum import (
                        DiarizationStatus,
                    )

                    error_msg = f"Processo encerrou inesperadamente com código {process.exitcode}"
                    repo.update_status(
                        cmd.diarization_id,
                        DiarizationStatus.FAILED.value,
                        error_message=error_msg,
                        status_message="Falha no processamento",
                    )

                    # Notify frontend via EventBus
                    event_bus = RedisEventBus()
                    event_bus.publish(
                        "ingestion_status",
                        {
                            "type": "diarization",
                            "id": cmd.diarization_id,
                            "status": DiarizationStatus.FAILED.value,
                            "message": f"Erro crítico no processamento: {error_msg}",
                        },
                    )
                finally:
                    db.close()
        else:
            logger.info("Audio diarization subprocess completed successfully")
    except Exception as e:
        logger.error(
            f"Worker Error: Failed to execute audio diarization: {e}", exc_info=True
        )
    finally:
        clear_global_context()
