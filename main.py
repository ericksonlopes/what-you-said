from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.logger import setup_logging
from src.presentation.api.routes import (
    chunk_router,
    ingest_router,
    job_router,
    search_router,
    source_router,
    subject_router,
)

logger = setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up WhatYouSaid API...")
    try:
        from src.infrastructure.repositories.sql.connector import Base, engine
        # In development, auto-create tables if they don't exist.
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified/created.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
    yield
    logger.info("Shutting down WhatYouSaid API...")


app = FastAPI(
    title="WhatYouSaid API",
    description="Vectorized data hub API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for React frontend (defaulting to localhost:3000 or 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://localhost(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include routes with the /rest prefix
app.include_router(search_router.router, prefix="/rest/search", tags=["Search"])
app.include_router(ingest_router.router, prefix="/rest/ingest", tags=["Ingestion"])
app.include_router(subject_router.router, prefix="/rest/subjects", tags=["Subjects"])
app.include_router(source_router.router, prefix="/rest/sources", tags=["Sources"])
app.include_router(job_router.router, prefix="/rest/jobs", tags=["Jobs"])
app.include_router(chunk_router.router, prefix="/rest/chunks", tags=["Chunks"])


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "message": "WhatYouSaid API is running"}


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(
        "main:app",
        host="localhost",
        port=5000,
        reload=True,
        log_config=None
    )
