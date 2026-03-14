# AGENTS.md

## Overview
This document provides essential knowledge for AI coding agents to be productive in the `WhatYouSaid` codebase. It highlights the architecture, workflows, conventions, and integration points specific to this project.

- Main layout:
    - `src/` — source code
    - `tests/` — automated tests
    - `alembic/`, `alembic.ini` — database migrations (Alembic)
    - `main.py` — entry point
    - `pyproject.toml`, `mypy.ini`, `pytest.ini` — tool configurations
---

## Big Picture Architecture

### Purpose
`WhatYouSaid` is a person-centric vectorized data hub designed to extract, process, and index information about people from various content sources (video, audio, text). It supports semantic search and Retrieval-Augmented Generation (RAG) workflows.

### Key Components
1. **Extractors**: Located in `src/infrastructure/extractors`, these modules handle data ingestion from sources like YouTube, audio, and text.
2. **Services**: Found in `src/infrastructure/services`, these orchestrate tasks like transcript splitting, embedding generation, and model loading.
3. **Repositories**: Adapters for vector stores (e.g., Weaviate, FAISS) are in
   `src/infrastructure/repository/vector_stores`.
4. **Domain Layer**: Defines entities and enums (e.g., `ChunkEntity`, `SourceType`) in `src/domain`.
5. **Configuration**: Managed via `src/config/settings.py` using `pydantic-settings`.
6. **Frontend (Streamlit)**: Dashboard UI located in `frontend/`.

### Data Flow
1. **Extraction**: Content is ingested via extractors.
2. **Processing**: Transcripts are split into chunks and embedded.
3. **Storage**: Chunks are stored in a vector database for retrieval.
4. **Search/RAG**: Data is queried for semantic search or RAG workflows.

---

## Frontend (Streamlit)

### Architecture
- **Entry point**: `frontend/streamlit_app.py`.
- **Tabs**: Modularized in `frontend/tabs/` (e.g., `content_sources.py`, `search.py`).
- **Dialogs**: Located in `frontend/dialogs/` (e.g., `add_knowledge_dialog.py`).

### Key Patterns
1. **Auto-refresh**: Use `@st.fragment(run_every="3s")` to refresh specific UI components (like the Tasks sidebar or the Content Sources table) without a full page reload.
2. **Ingestion Workflow**:
    - **Foreground (Immediate)**: Extract metadata (e.g., Video ID), create `ContentSource` with `pending` status, and create `IngestionJob` with `started` status.
    - **Background (Async)**: Trigger the heavy lifting via `frontend/utils/background_jobs.py`, passing the pre-created `job_id`.
    - **Sync**: Use `st.rerun()` after starting the job (ensure it's not inside an `on_click` callback) to show the new task immediately.
3. **Styling**: 
    - Custom CSS is injected via `TABLE_CSS` in `streamlit_app.py`.
    - Use `.task-card` for task history items for consistent layout.
    - Badges follow `.badge-done`, `.badge-processing`, etc.

---

## Developer Workflows

### Setup
- Use Python 3.12+.
- Create and activate a virtual environment:
  ```bash
  python -m venv .venv
  .\.venv\Scripts\Activate
  ```
- Install dependencies:
  ```bash
  python -m pip install -e .
  uv sync
  ```

### Testing
- Run all tests:
  ```bash
  pytest -v
  ```
- Run a specific test:
  ```bash
  pytest -q tests/path/to/test_file.py::test_function_name
  ```
- Check coverage:
  ```bash
  pytest --cov=src --cov-report=xml
  ```

### Static Checks
- Type checking:
  ```bash
  mypy src tests
  ```
- Formatting:
  ```bash
  black .
  ```
- Import sorting:
  ```bash
  isort .
  ```

### Database Migrations
- Create a migration:
  ```bash
  alembic revision --autogenerate -m "description"
  ```
- Apply migrations:
  ```bash
  alembic upgrade head
  ```
- Downgrade migrations:
  ```bash
  alembic downgrade -1
  ```

---

## Project-Specific Conventions

### Environment Variables
- Managed via `.env` file.
- Nested variables use `__` as a delimiter (e.g., `VECTOR__WEAVIATE_HOST`).
- Example:
  ```env
  APP__ENV=development
  VECTOR__STORE_TYPE=weaviate
  VECTOR__WEAVIATE_HOST=localhost
  VECTOR__WEAVIATE_PORT=8081
  ```

### Vector Store Integration
- Adapters for vector databases are in `src/infrastructure/repositories/vector_stores`.
- Examples include Weaviate, FAISS, and Pinecone.

### Logging
- Configured in `src/config/logger.py`.
- Log levels are controlled via `APP__LIST_LOG_LEVELS`.

---

## Integration Points

### External Dependencies
- **Vector Databases**: Supports Weaviate, FAISS, Pinecone, etc.
- **Embedding Models**: Abstracted via `EmbeddingService`.

### Cross-Component Communication
- Services orchestrate workflows between extractors, repositories, and vector stores.
- Configuration is centralized in `src/config/settings.py`.

---

## Examples and Notes
- Migration tips: `alembic/README.md`.

---

## Troubleshooting

### Common Issues
- **Validation Errors**: Check `.env` for missing or incorrect variables.
- **Vector Store Connection**: Verify `VECTOR__WEAVIATE_HOST` and `VECTOR__WEAVIATE_PORT`.

### Debugging Tips
- Use `pytest -k "keyword"` to isolate failing tests.
- Check logs for detailed error messages.

---

This document is a living guide. Update it as the project evolves.

---

## Copilot / Contributors instructions (consolidated)

O conteúdo de orientação para Copilot/Contributors que estava em `copilot-instructions.md` foi consolidado aqui para
evitar duplicação. Principais pontos resumidos:

- Ambiente e instalação: Python 3.12+, python -m venv .venv, .\.venv\Scripts\Activate, python -m pip install -e .; use
  `uv install` / `uv sync` quando aplicável.
- Testes e qualidade: pytest -v, pytest -q, mypy src tests, black ., isort .
- Migrações: alembic upgrade head; alembic revision --autogenerate -m "description"
- Convenções: Faça mudanças cirúrgicas; planeje alterações complexas (use plan.md); atualize docs e testes ao alterar
  comportamento público.
- Fluxo de planejamento: use `plan.md` na sessão para mudanças complexas e a tabela `todos` para acompanhamento.
- Ferramentas do Copilot CLI: prefira `create`/`edit` para mudanças em arquivos; use backslash em caminhos no Windows.
- Commit/PR: mensagens curtas; inclua este trailer obrigatório em todos os commits quando aplicável:

- Checklist rápido antes do commit: todos os testes passam; mypy sem erros relevantes; código formatado (black, isort);
  documentação atualizada.

Para uma cópia completa e histórica das instruções, verifique `.github/copilot-instructions.md`.

