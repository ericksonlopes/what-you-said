<div align="center">

# WhatYouSaid

[![codecov](https://codecov.io/github/ericksonlopes/WhatYouSaid/branch/main/graph/badge.svg?token=8CZJARVJUE)](https://codecov.io/github/ericksonlopes/WhatYouSaid)

[![Tests](https://github.com/ericksonlopes/WhatYouSaid/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/ericksonlopes/WhatYouSaid/actions/workflows/tests.yml)
[![Code Quality](https://github.com/ericksonlopes/WhatYouSaid/actions/workflows/code-quality.yml/badge.svg?branch=main)](https://github.com/ericksonlopes/WhatYouSaid/actions/workflows/code-quality.yml)
[![Security](https://github.com/ericksonlopes/WhatYouSaid/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/ericksonlopes/WhatYouSaid/actions/workflows/security.yml)

![Python](https://img.shields.io/badge/-Python-3776AB?&logo=Python&logoColor=FFFFFF)
![React](https://img.shields.io/badge/-React-61DAFB?&logo=React&logoColor=000000)
![Tailwind CSS](https://img.shields.io/badge/-Tailwind_CSS-38B2AC?&logo=Tailwind%20CSS&logoColor=FFFFFF)
![Redis](https://img.shields.io/badge/-Redis-DC382D?&logo=Redis&logoColor=FFFFFF)
![Pytest](https://img.shields.io/badge/-Pytest-0A9EDC?&logo=Pytest&logoColor=FFFFFF)
![GitHub Actions](https://img.shields.io/badge/-GitHub%20Actions-2088FF?&logo=GitHub%20Actions&logoColor=FFFFFF)

</div>

WhatYouSaid is a vectorized data hub designed to explore any topic or knowledge domain. It extracts, processes, and indexes content from YouTube videos, local files, and remote URLs to enable advanced semantic search and Retrieval-Augmented Generation (RAG) workflows.

This repository provides modular extractors, robust splitting utilities, and a scalable background processing pipeline to build searchable knowledge bases efficiently.

---

## 📚 Documentation

Detailed guides for specific topics:

- 🐳 **[Docker Deployment Guide](docs/docker-deployment.md)**: Learn how to use Docker Profiles to run different combinations of databases (MySQL, Postgres, SQLite) and vector stores (FAISS, Weaviate).

---

## 🚀 Features

- **Multi-source Extraction**: Ingest data from YouTube (transcripts), local files (PDF, DOCX, TXT), and **remote URLs** via the Docling engine.
- **Robust Fallbacks**: Integrated `PlainTextExtractor` ensuring successful ingestion even for formats not supported by specialized extractors.
- **Async Task Queue**: High-performance background processing powered by **Redis**, ensuring responsive ingestion workflows.
- **Real-time Updates**: Live ingestion status and progress monitoring via a **Redis Event Bus** (SSE-ready).
- **Advanced Search**: Semantic, keyword (BM25), and **Hybrid Search** with cross-encoder re-ranking for maximum precision.
- **Pluggable Vector Stores**: Support for **FAISS** (local), **ChromaDB**, and **Weaviate** (scalable).
- **Pluggable SQL Databases**: Support for **SQLite**, **PostgreSQL**, **MySQL**, **MariaDB**, and **MSSQL**.
- **Modern Dashboard**: A clean React + Tailwind CSS frontend for managing knowledge subjects, content sources, and monitoring background tasks.

---

## 🛠️ Infrastructure & Deployment

WhatYouSaid is designed to be flexible, from a lightweight local setup to a scalable production-ready environment.

### 1. Storage & Messaging Options

| Component | Lightweight (Local) | Scalable / Production |
| :--- | :--- | :--- |
| **Relational Database** | **SQLite** (Default, file-based) | **PostgreSQL**, **MySQL**, **MariaDB**, **MSSQL** |
| **Vector Store** | **FAISS** (Local, file-based) | **Weaviate** (Container or Cloud), **ChromaDB** |
| **Task Queue & Bus** | **In-memory** (Limited) | **Redis** (Default in Docker) |

### 2. Docker Compose Profiles

We use **Docker Profiles** to keep the environment lean. Only the services you need are started.

> 📘 **Detailed Guide**: For a step-by-step tutorial on different deployment scenarios, see our [Docker Deployment Guide](docs/docker-deployment.md).

#### **Scenario A: Lite (Default)**
Uses **SQLite**, **FAISS**, and **Redis**.
```bash
docker-compose up -d
```

#### **Scenario B: Scalable (Base)**
Starts **PostgreSQL**, **Weaviate**, and **Redis**.
```bash
docker-compose --profile base up -d
# Note: Set SQL__TYPE=postgres and VECTOR__STORE_TYPE=weaviate in .env
```

---

## 🏗️ Architecture

The system follows a clean architecture approach, ensuring separation of concerns:

- **Application Layer**: Contains use cases (e.g., `FileIngestionUseCase`, `SearchUseCase`) and a `ServiceRegistry` for background worker dependency resolution.
- **Infrastructure Layer**:
  - `extractors/`: Fetch raw content (Docling, YouTube, PlainText).
  - `repositories/`: Data persistence (SQLAlchemy for relational, specialized clients for Vector Stores).
  - `services/`: Core logic (text splitting, embedding, re-ranking, Redis task queue).
- **Presentation Layer**: FastAPI-based REST API with real-time SSE notifications.

---

## 🧪 Quality & Testing

We maintain a high standard of code quality and test coverage:

- **417+ Automated Tests**: Covering unit, integration, and complex edge cases.
- **93% Code Coverage**: Verified via `pytest-cov`.
- **Strict Linting**: Powered by `ruff` for code style and `mypy` for static type checking.
- **Security Scanning**: Integrated `bandit` scans for vulnerability detection.

**Run tests locally:**
```bash
uv run pytest
```

---

## 🤝 Contributing

Contributions are welcome. Please:
- Open an issue to discuss major changes.
- Add tests for any new feature or bug fix.
- Ensure `ruff check .` and `mypy .` pass before submitting.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

<div align="center">
    <p>Made with ❤️ by Erickson Lopes </p>

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Erickson_Lopes-blue)](https://www.linkedin.com/in/ericksonlopes/)

</div>
