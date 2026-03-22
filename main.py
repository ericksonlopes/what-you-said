from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.logger import setup_logging
from src.presentation.api.middleware.trace_middleware import TraceMiddleware
from src.presentation.api.routes import (
    chunk_router,
    ingest_router,
    job_router,
    notification_router,
    search_router,
    settings_router,
    source_router,
    subject_router,
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
        from src.infrastructure.services.redis_task_queue_service import (
            RedisTaskQueueService,
        )
        from src.infrastructure.services.redis_event_bus import RedisEventBus

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

        app.state.model_loader = ModelLoaderService(
            model_name=_settings.model_embedding.name
        )
        logger.info("Embedding model pre-loaded successfully.")

        # Load Re-rank Model
        logger.info(
            "Loading Re-rank Model",
            context={"model_name": _settings.model_rerank.name},
        )
        app.state.rerank_service = ReRankService(model_name=_settings.model_rerank.name)
        logger.info("Re-rank model pre-loaded successfully.")

        # Initialize Redis Task Queue
        logger.info("Initializing RedisTaskQueueService...")
        app.state.task_queue = RedisTaskQueueService(num_workers=4)
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

# Include routes with the /rest prefix
app.include_router(search_router.router, prefix="/rest/search", tags=["Search"])
app.include_router(ingest_router.router, prefix="/rest/ingest", tags=["Ingestion"])
app.include_router(subject_router.router, prefix="/rest/subjects", tags=["Subjects"])
app.include_router(source_router.router, prefix="/rest/sources", tags=["Sources"])
app.include_router(job_router.router, prefix="/rest/jobs", tags=["Jobs"])
app.include_router(settings_router.router, prefix="/rest/settings", tags=["Settings"])
app.include_router(chunk_router.router, prefix="/rest/chunks", tags=["Chunks"])
app.include_router(
    notification_router.router, prefix="/rest/notifications", tags=["Notifications"]
)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "WhatYouSaid API is running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=5000, reload=True, log_config=None)
