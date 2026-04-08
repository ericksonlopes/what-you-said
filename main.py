import os

# ruff: noqa: E402
import warnings
from contextlib import asynccontextmanager

# Suppress NNPACK warnings (Unsupported hardware)
os.environ["NNPACK_CPU_FAST_8x8_CONV"] = "0"

# Silence torchcodec loading warnings since it's a beta component and often
# causes DLL discovery issues on Windows that don't affect the core app.
warnings.filterwarnings("ignore", category=UserWarning, module="torchcodec")

from fastapi import Depends, FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from src.config.logger import setup_logging  # noqa: E402
from src.presentation.api.dependencies import get_current_user  # noqa: E402
from src.presentation.api.middleware.trace_middleware import (
    TraceMiddleware,  # noqa: E402
)
from src.presentation.api.routes import (  # noqa: E402
    audio_diarization_and_recognition_router as audio_router,
)
from src.presentation.api.routes import (  # noqa: E402
    auth_router,
    chunk_router,
    duplicate_router,
    ingest_router,
    job_router,
    notification_router,
    search_router,
    settings_router,
    source_router,
    subject_router,
)
from src.presentation.api.routes import (
    voice_profile_management_router as voice_router,  # noqa: E402
)

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.application.service_registry import registry

    registry.register("app", app)

    logger.info("Starting up WhatYouSaid API...")

    try:
        from src.config.settings import Settings
        from src.infrastructure.services.model_loader_service import ModelLoaderService
        from src.infrastructure.services.re_rank_service import ReRankService
        from src.infrastructure.services.redis_event_bus import RedisEventBus
        from src.infrastructure.services.redis_task_queue_service import (
            RedisTaskQueueService,
        )

        logger.info("Initializing Settings...")
        _settings = Settings()

        # Initialize Redis Event Bus
        logger.info("Initializing RedisEventBus...")
        app.state.event_bus = RedisEventBus()

        # Load Embedding Model
        logger.info(
            "Loading Embedding Model",
            context={
                "model_name": _settings.model_embedding.name,
                "device": _settings.app.device,
            },
        )

        app.state.model_loader = ModelLoaderService(model_name=_settings.model_embedding.name)
        logger.info("Embedding model pre-loaded successfully.")

        # Load Re-rank Model
        logger.info(
            "Loading Re-rank Model",
            context={"model_name": _settings.model_rerank.name},
        )
        app.state.rerank_service = ReRankService(model_name=_settings.model_rerank.name)
        logger.info("Re-rank model pre-loaded successfully.")

        # Register worker tasks and initialize Redis Task Queue
        from src.application.workers import (
            run_audio_diarization_dispatcher_worker,
            run_audio_diarization_worker,
            run_diarization_ingestion_worker,
            run_duplicate_detection_worker,
            run_file_ingestion_worker,
            run_web_ingestion_worker,
            run_youtube_dispatcher_worker,
            run_youtube_ingestion_worker,
        )
        from src.infrastructure.services.redis_task_queue_service import register_task

        register_task("run_file_ingestion_worker", run_file_ingestion_worker)
        register_task("run_youtube_ingestion_worker", run_youtube_ingestion_worker)
        register_task("run_web_ingestion_worker", run_web_ingestion_worker)
        register_task("run_audio_diarization_worker", run_audio_diarization_worker)
        register_task("run_diarization_ingestion_worker", run_diarization_ingestion_worker)
        register_task("run_youtube_dispatcher_worker", run_youtube_dispatcher_worker)
        register_task(
            "run_audio_diarization_dispatcher_worker",
            run_audio_diarization_dispatcher_worker,
        )
        register_task("run_duplicate_detection_worker", run_duplicate_detection_worker)

        logger.info("Initializing RedisTaskQueueService...")
        app.state.task_queue = RedisTaskQueueService(num_workers=1)
        app.state.task_queue.start()
        logger.info("RedisTaskQueueService started.")

    except Exception as e:
        logger.error(e, context={"action": "pre_load_models"})
        if not hasattr(app.state, "model_loader"):
            app.state.model_loader = None
        if not hasattr(app.state, "rerank_service"):
            app.state.rerank_service = None
        if not hasattr(app.state, "task_queue"):
            app.state.task_queue = None

    yield

    if hasattr(app.state, "task_queue") and app.state.task_queue:
        app.state.task_queue.stop()

    logger.info("Shutting down WhatYouSaid API...")


app = FastAPI(
    title="WhatYouSaid API",
    description="Vectorized data hub API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(TraceMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://localhost(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router.router, prefix="/rest/auth", tags=["Auth"])


secured_deps = [Depends(get_current_user)]

app.include_router(
    search_router.router,
    prefix="/rest/search",
    tags=["Search"],
    dependencies=secured_deps,
)
app.include_router(
    ingest_router.router,
    prefix="/rest/ingest",
    tags=["Ingestion"],
    dependencies=secured_deps,
)
app.include_router(
    subject_router.router,
    prefix="/rest/subjects",
    tags=["Subjects"],
    dependencies=secured_deps,
)
app.include_router(
    source_router.router,
    prefix="/rest/sources",
    tags=["Sources"],
    dependencies=secured_deps,
)
app.include_router(job_router.router, prefix="/rest/jobs", tags=["Jobs"], dependencies=secured_deps)
app.include_router(
    settings_router.router,
    prefix="/rest/settings",
    tags=["Settings"],
    dependencies=secured_deps,
)
app.include_router(
    chunk_router.router,
    prefix="/rest/chunks",
    tags=["Chunks"],
    dependencies=secured_deps,
)
app.include_router(
    duplicate_router.router,
    prefix="/rest/duplicates",
    tags=["Duplicates"],
    dependencies=secured_deps,
)
app.include_router(
    notification_router.router,
    prefix="/rest/notifications",
    tags=["Notifications"],
)
app.include_router(
    audio_router.router,
    prefix="/rest/audio",
    tags=["Audio Diarization & Recognition"],
    dependencies=secured_deps,
)
app.include_router(
    voice_router.router,
    prefix="/rest/voices",
    tags=["Voice Profiles"],
    dependencies=secured_deps,
)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "WhatYouSaid API is running"}


if __name__ == "__main__":
    import uvicorn

    from src.config.settings import settings

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=settings.app.port,
        reload=True,
        log_config=None,
    )
