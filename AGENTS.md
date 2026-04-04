# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Is

WhatYouSaid is a vectorized data hub that extracts, processes, and indexes content from YouTube videos, local files, remote URLs, and websites for semantic search and RAG workflows. It has a Python/FastAPI backend and a React/TypeScript frontend.

## Common Commands

### Backend
```bash
uv sync --group dev                    # Install all deps (including dev)
uv run pytest                          # Run all tests with coverage
uv run pytest tests/path/test_file.py  # Run a single test file
uv run pytest -m MarkerName            # Run tests by marker (see pytest.ini for markers)
uv run ruff check . --fix              # Lint and autofix
uv run mypy .                          # Type checking (ignores test files)
uv run bandit -r src/                  # Security scan
python main.py                         # Run API server (dev mode with reload)
alembic upgrade head                   # Apply database migrations
alembic revision --autogenerate -m ""  # Generate a migration
```

### Frontend
```bash
cd frontend && npm install && npm run dev
```

### Docker
```bash
docker-compose up -d                         # Lite: SQLite + FAISS + Redis
docker-compose --profile base up -d          # Scalable: Postgres + Weaviate + Redis
```

## Architecture

Clean architecture with DDD-style layering:

- **`src/domain/`** - Entities, enums, interfaces (ports), mappers. No framework imports.
  - `interfaces/` defines contracts: `IVectorRepository`, `IEventBus`, `ITaskQueue`, extractors, logger
  - `mappers/` converts between domain entities and SQL/vector models
- **`src/application/`** - Use cases orchestrate domain logic. Workers (`workers.py`) are background task entry points dispatched via `ServiceRegistry`.
  - `dtos/commands/` - Input DTOs for ingestion (file, web, youtube)
  - `dtos/results/` - Output DTOs for search and ingestion results
  - `service_registry.py` - Singleton registry for resolving dependencies in background workers
- **`src/infrastructure/`** - Concrete implementations
  - `extractors/` - YouTube (yt-dlp + transcript API), Docling (PDF/DOCX/URL), Crawl4AI (websites), PlainText (fallback)
  - `repositories/sql/` - SQLAlchemy repos (SQLite, Postgres, MySQL, MariaDB, MSSQL)
  - `repositories/vector/` - Vector store repos (FAISS, Weaviate, ChromaDB, Qdrant) all implementing `IVectorRepository`
  - `services/` - Embedding, text splitting, re-ranking, Redis task queue, Redis event bus (SSE)
- **`src/presentation/api/`** - FastAPI routes, schemas, middleware. All routes under `/rest/` prefix.
  - `dependencies.py` - FastAPI dependency injection (auth, services)
  - `middleware/trace_middleware.py` - Request correlation IDs
- **`src/config/`** - Pydantic Settings with `__` delimiter for nested env vars (e.g., `VECTOR__STORE_TYPE`)
- **`main.py`** - FastAPI app with lifespan that loads ML models, starts Redis task queue, registers workers
- **`frontend/`** - React + TypeScript + Tailwind CSS dashboard

## Key Patterns

- **Environment variables** use double-underscore `__` as nested delimiter for Pydantic Settings (e.g., `SQL__TYPE`, `VECTOR__STORE_TYPE`, `REDIS__HOST`). See `.env.example`.
- **Pluggable stores**: Vector store and SQL database are selected at runtime via config. Adding a new vector store means implementing `IVectorRepository`. Optional dependency groups in `pyproject.toml` (`faiss`, `chroma`, `weaviate`, `qdrant`, `postgres`, `mysql`, `mariadb`, `mssql`) must be installed for the chosen backend.
- **Background processing**: Ingestion tasks are queued via `RedisTaskQueueService` and executed by workers registered in `main.py` lifespan. Real-time progress is pushed through `RedisEventBus` (SSE).
- **IngestionContext**: `src/application/ingestion_context.py` is a dataclass grouping shared dependencies (services, event bus, settings) for all ingestion use cases. Workers resolve it via `dependencies.resolve_ingestion_context(app)`.
- **Audio diarization workers** spawn a separate process via `multiprocessing.get_context("spawn")` to avoid torch/CUDA thread deadlocks inside Redis worker daemon threads. This is intentional — do not refactor to run in-thread.
- **SQL connector globals**: `src/infrastructure/repositories/sql/connector.py` creates module-level `engine` and `Session` at import time from settings. Tests must monkey-patch these globals (see `conftest.py`'s `sqlite_memory` fixture).
- **Tests** mirror `src/` structure under `tests/`. The `conftest.py` provides an in-memory SQLite fixture (`sqlite_memory`) and mocks auth globally. Tests use `pytest` markers extensively (see `pytest.ini`).
- **Coverage** excludes entities, models, DTOs, schemas, mappers, and scripts (see `.coveragerc`).
- **Agent skills and workflows** live in `.agents/skills/` and `.agents/workflows/` (see `AGENTS.md`).

## API Route Prefixes

All routes are under `/rest/` — auth at `/rest/auth`, ingestion at `/rest/ingest`, search at `/rest/search`, audio diarization at `/rest/audio`, voice profiles at `/rest/voices`. The `/health` endpoint is unauthenticated. All other routes require JWT auth via `get_current_user` dependency.

## Python Version

Requires Python 3.12 (pinned in `pyproject.toml` and `.python-version`).