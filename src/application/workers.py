import logging
from typing import Any

from src.application.dtos.commands.ingest_diarization_command import (
    IngestDiarizationCommand,
)
from src.application.dtos.commands.ingest_file_command import IngestFileCommand
from src.application.dtos.commands.ingest_web_command import IngestWebCommand
from src.application.dtos.commands.ingest_youtube_command import IngestYoutubeCommand
from src.application.dtos.commands.process_audio_command import ProcessAudioCommand
from src.application.dtos.commands.train_voice_command import TrainVoiceCommand
from src.application.service_registry import registry
from src.infrastructure.loggers.std_logger import (
    clear_global_context,
    set_global_context,
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
        from src.application.use_cases.file_ingestion_use_case import (
            FileIngestionUseCase,
        )
        from src.infrastructure.services.chunk_vector_service import ChunkVectorService
        from src.presentation.api.dependencies import (
            resolve_ingestion_context,
            resolve_rerank_service,
            resolve_vector_repository,
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
        logger.error(f"Worker Error: Failed to execute file ingestion: {e}", exc_info=True)
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
        from src.application.use_cases.youtube_ingestion_use_case import (
            YoutubeIngestionUseCase,
        )
        from src.infrastructure.services.youtube_vector_service import (
            YouTubeVectorService,
        )
        from src.presentation.api.dependencies import (
            resolve_ingestion_context,
            resolve_vector_repository,
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
        logger.error(f"Worker Error: Failed to execute YouTube ingestion: {e}", exc_info=True)
    finally:
        clear_global_context()


def run_youtube_dispatcher_worker(cmd: IngestYoutubeCommand):
    """Background dispatcher worker for YouTube playlists or bulk video lists.

    Resolves the list of URLs and enqueues individual workers for each video.
    """
    set_global_context({"correlation_id": _get_correlation_id(cmd, "worker-youtube-dispatcher")})

    if isinstance(cmd, dict):
        cmd = IngestYoutubeCommand(**cmd)

    app = _get_app()
    if not app:
        clear_global_context()
        return

    try:
        from src.application.dtos.enums.youtube_data_type import YoutubeDataType
        from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor

        task_queue = app.state.task_queue

        # 1. Resolve the full list of URLs
        video_list = []
        if cmd.data_type == YoutubeDataType.PLAYLIST:
            # We need to resolve the playlist entries
            playlist_url = cmd.video_url or (cmd.video_urls[0] if cmd.video_urls else None)
            if not playlist_url:
                logger.warning("No URL provided for playlist dispatcher")
                return

            extractor = YoutubeExtractor(language=cmd.language)
            video_list = extractor.extract_playlist_videos(playlist_url)
        elif cmd.data_type == YoutubeDataType.CHANNEL:
            # Resolve the channel entries
            channel_url = cmd.video_url or (cmd.video_urls[0] if cmd.video_urls else None)
            if not channel_url:
                logger.warning("No URL provided for channel dispatcher")
                return

            extractor = YoutubeExtractor(language=cmd.language)
            videos, _ = extractor.extract_channel_videos(channel_url)
            video_list = [v["url"] for v in videos]
        elif cmd.video_urls:
            video_list = [v for v in cmd.video_urls if v]

        if not video_list:
            logger.warning(f"YouTube Dispatcher resolved 0 videos for type {cmd.data_type}.")
            return

        logger.info(f"YouTube Dispatcher resolved {len(video_list)} videos. Enqueueing individual tasks...")

        # 2. Enqueue each video as a separate task
        for url in video_list:
            # Create a clone of the command for a single video
            # IMPORTANT: We don't reuse the same ingestion_job_id from the dispatcher
            # so that each video can either create its own tracking or we let the use case handle it.
            single_cmd = IngestYoutubeCommand(
                video_url=url,
                subject_id=cmd.subject_id,
                subject_name=cmd.subject_name,
                title=None,  # Use extractor to find title in the child worker
                data_type=YoutubeDataType.VIDEO,
                language=cmd.language,
                tokens_per_chunk=cmd.tokens_per_chunk,
                tokens_overlap=cmd.tokens_overlap,
                reprocess=cmd.reprocess,
            )

            task_queue.enqueue(
                run_youtube_ingestion_worker,
                single_cmd,
                task_title=f"YouTube: {url}",
                metadata={"parent_dispatcher_job": str(cmd.ingestion_job_id)} if cmd.ingestion_job_id else {},
            )

        logger.info(f"Successfully dispatched {len(video_list)} YouTube ingestion tasks.")

    except Exception as e:
        logger.error(f"YouTube Dispatcher Worker Error: {e}", exc_info=True)
    finally:
        clear_global_context()


def run_diarization_ingestion_worker(cmd: IngestDiarizationCommand):
    """Background worker function for direct diarization ingestion."""
    set_global_context({"correlation_id": _get_correlation_id(cmd, "worker-diarization")})

    app = _get_app()
    if not app:
        clear_global_context()
        return

    try:
        from src.application.use_cases.diarization_ingestion_use_case import (
            DiarizationIngestionUseCase,
        )
        from src.infrastructure.repositories.sql.diarization_repository import (
            DiarizationRepository,
        )
        from src.infrastructure.services.chunk_vector_service import ChunkVectorService
        from src.presentation.api.dependencies import (
            resolve_ingestion_context,
            resolve_rerank_service,
            resolve_vector_repository,
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
        logger.error(f"Worker Error: Failed to execute diarization ingestion: {e}", exc_info=True)
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
            from src.application.use_cases.web_scraping_use_case import (
                WebScrapingUseCase,
            )
            from src.infrastructure.services.chunk_vector_service import (
                ChunkVectorService,
            )
            from src.presentation.api.dependencies import (
                get_web_extractor,
                resolve_ingestion_context,
                resolve_rerank_service,
                resolve_vector_repository,
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
            logging.getLogger(__name__).error(f"Worker Error: Failed to execute Web Scraping: {e}", exc_info=True)
        finally:
            clear_global_context()

    asyncio.run(_run())


def _audio_diarization_subprocess(cmd_dict: dict):
    """Run audio diarization in a separate process to avoid torch/CUDA thread deadlocks."""
    from src.application.use_cases.process_audio_diarization_pipeline import (
        ProcessAudioDiarizationPipelineUseCase,
    )
    from src.infrastructure.repositories.sql.connector import (
        Session as DBSessionFactory,
    )
    from src.infrastructure.repositories.sql.content_source_repository import (
        ContentSourceSQLRepository,
    )
    from src.infrastructure.repositories.sql.diarization_repository import (
        DiarizationRepository,
    )
    from src.infrastructure.services.content_source_service import ContentSourceService
    from src.infrastructure.services.redis_event_bus import RedisEventBus

    db = DBSessionFactory()
    event_bus = RedisEventBus()
    cs_repo = ContentSourceSQLRepository()
    cs_service = ContentSourceService(cs_repo)

    diarization_id = cmd_dict.get("diarization_id")
    try:
        use_case = ProcessAudioDiarizationPipelineUseCase(db, event_bus=event_bus, cs_service=cs_service)
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


def run_audio_diarization_dispatcher_worker(cmd: ProcessAudioCommand):
    """Dispatcher worker for YouTube playlists/channels diarization.

    Resolves a playlist/channel into individual video URLs and enqueues
    a separate diarization task for each one.
    """
    set_global_context({"correlation_id": "dispatcher-audio-youtube"})

    app = _get_app()
    if not app:
        clear_global_context()
        return

    try:
        from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor
        from src.infrastructure.repositories.sql.connector import (
            Session as DBSessionFactory,
        )
        from src.infrastructure.repositories.sql.diarization_repository import (
            DiarizationRepository,
        )

        task_queue = app.state.task_queue
        db = DBSessionFactory()
        repo = DiarizationRepository(db)

        # Detect YouTube Channel vs Playlist
        is_channel = "/channel/" in cmd.source or "/c/" in cmd.source or "/user/" in cmd.source or "@" in cmd.source

        logger.info(
            "Resolving %s URLs for diarization: %s",
            "channel" if is_channel else "playlist",
            cmd.source,
        )

        extractor = YoutubeExtractor(language=cmd.language)
        video_list = []

        if is_channel:
            videos, _ = extractor.extract_channel_videos(cmd.source)
            video_list = [v["url"] for v in videos]
        else:
            video_list = extractor.extract_playlist_videos(cmd.source)

        if not video_list:
            logger.warning(
                "No videos found in %s: %s",
                "channel" if is_channel else "playlist",
                cmd.source,
            )
            return

        for url in video_list:
            # Check for duplicates before creation
            existing = repo.get_by_external_source(
                source_type=cmd.source_type,
                external_source=url,
                subject_id=cmd.subject_id,
            )

            if (
                existing and existing.status != "failed"  # DiarizationStatus is not imported here as Enum yet
            ):
                logger.info("Skipping duplicate video for diarization dispatcher: %s", url)
                continue

            # 1. Create a pending record
            pending = repo.create_pending(
                name=url,
                source_type=cmd.source_type,
                external_source=url,
                language=cmd.language,
                model_size=cmd.model_size,
                subject_id=cmd.subject_id,
            )

            # 2. Create the command for this specific video
            single_cmd = ProcessAudioCommand(
                source_type=cmd.source_type,
                source=url,
                language=cmd.language,
                num_speakers=cmd.num_speakers,
                min_speakers=cmd.min_speakers,
                max_speakers=cmd.max_speakers,
                model_size=cmd.model_size,
                recognize_voices=cmd.recognize_voices,
                diarization_id=str(pending.id),
            )

            # 3. Enqueue the actual worker
            task_queue.enqueue(
                run_audio_diarization_worker,
                single_cmd,
                task_title=f"Diarização: {url}",
                metadata={"parent_dispatcher": cmd.source},
            )

        logger.info(f"Successfully dispatched {len(video_list)} diarization tasks.")

    except Exception as e:
        logger.error(f"Audio Diarization Dispatcher Worker Error: {e}", exc_info=True)
    finally:
        if "db" in locals():
            db.close()
        clear_global_context()


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
            logger.error("Audio diarization subprocess exited with code %d", process.exitcode)
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
        logger.error(f"Worker Error: Failed to execute audio diarization: {e}", exc_info=True)
    finally:
        clear_global_context()


def run_voice_training_worker(cmd: TrainVoiceCommand):
    """Background worker function for voice profile training from speaker segment."""
    # Redis-serialized payloads arrive as dicts — convert BEFORE touching fields.
    if isinstance(cmd, dict):
        cmd = TrainVoiceCommand(**cmd)

    set_global_context({"correlation_id": f"worker-voice-train-{cmd.name}"})

    app = _get_app()
    if not app:
        clear_global_context()
        return

    try:
        from src.application.use_cases.manage_voice_profiles import (
            TrainVoiceProfileFromSpeakerSegmentUseCase,
        )
        from src.infrastructure.repositories.sql.connector import Session as DBSession
        from src.presentation.api.dependencies import resolve_ingestion_context

        ctx = resolve_ingestion_context(app)
        db = DBSession()
        try:
            use_case = TrainVoiceProfileFromSpeakerSegmentUseCase(db, event_bus=ctx.event_bus)
            use_case.execute(
                diarization_id=cmd.diarization_id,
                speaker_label=cmd.speaker_label,
                name=cmd.name,
            )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Worker Error: Failed to execute voice training: {e}", exc_info=True)
    finally:
        clear_global_context()
