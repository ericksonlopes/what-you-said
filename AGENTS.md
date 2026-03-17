# 🗺️ WhatYouSaid Agent Guide (Architecture & Workflows)

Este documento serve como a "Bússola Arquitetural" para agentes de IA no projeto. Para fluxos de trabalho especializados (testes, commits, banco de dados), consulte as **Skills** em `.agents/skills/`.

## 🏗️ Big Picture Architecture

### Propósito
O `WhatYouSaid` é um hub de dados vetorizados centrado em pessoas, projetado para extrair, processar e indexar informações de diversas fontes (YouTube, Áudio, Texto) para busca semântica e RAG.

### Estrutura do Projeto
- `src/domain/`: Entidades, Enums e Interfaces (DDD).
- `src/application/`: Casos de Uso (Orquestração).
- `src/infrastructure/`: Implementações concretas (Extratores, Repositórios SQL/Vetor, Serviços de LLM).
- `src/presentation/api/`: Rotas FastAPI e Schemas.
- `frontend/`: Dashboard React/TypeScript.
- `tests/`: Estrutura espelhada do `src/`.

---

## 💻 Developer Workflows

### Setup Rápido (Backend)
```bash
python -m venv .venv
.\.venv\Scripts\Activate
uv sync --group dev
python -m pip install -e .
```

### Setup Rápido (Frontend)
```bash
cd frontend
npm install
npm run dev
```

### Comandos de Infraestrutura
- **Migrações (Alembic)**: `alembic upgrade head`
- **Docker Compose**: `docker compose -f .devcontainer/docker-compose.yml up --build`
- **Testes (Pytest)**: `pytest`
- **Qualidade**: `ruff check . --fix`, `mypy .`, `bandit -r src/`

---

## 🎨 Frontend (React/TypeScript)

- **Entry point**: `frontend/src/App.tsx`.
- **State**: Gerenciado via `AppContext` em `frontend/src/store/`.
- **Services**: Comunicação com a API em `frontend/src/services/api.ts`.

---

## 🔧 Convenções do Projeto

- **Variáveis de Ambiente**: Delimitador duplo `__` para variáveis aninhadas no Pydantic (ex: `VECTOR__STORE_TYPE`).
- **Timezones**: Sempre use `datetime.now(timezone.utc)`.
- **Testes**: Novos arquivos em `src/` exigem testes correspondentes em `tests/` (verifique a Skill `secure-commit`).

---

## 🧠 Integrações e LLMs
- **Vector Stores**: Suporte nativo para Weaviate e FAISS via `IVectorRepository`.
- **Embeddings**: Abstraídos via `EmbeddingService`. Modelos padrão: `BAAI/bge-m3`.

---
*Este guia deve ser mantido atualizado conforme a arquitetura evolui.*
