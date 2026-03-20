<div align="center">

# WhatYouSaid

[![codecov](https://codecov.io/github/ericksonlopes/WhatYouSaid/branch/main/graph/badge.svg?token=8CZJARVJUE)](https://codecov.io/github/ericksonlopes/WhatYouSaid)

[![Tests](https://github.com/ericksonlopes/what-you-said/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/ericksonlopes/what-you-said/actions/workflows/python-tests.yml)
[![Code Quality](https://github.com/ericksonlopes/what-you-said/actions/workflows/code-quality.yml/badge.svg?branch=main)](https://github.com/ericksonlopes/what-you-said/actions/workflows/code-quality.yml)
[![Security](https://github.com/ericksonlopes/what-you-said/actions/workflows/security.yml/badge.svg?branch=main)](https://github.com/ericksonlopes/what-you-said/actions/workflows/security.ymll)

![Python](https://img.shields.io/badge/-Python-3776AB?&logo=Python&logoColor=FFFFFF)
![LangChain](https://img.shields.io/badge/-LangChain-1C3C3C?&logo=LangChain&logoColor=FFFFFF)
![Pytest|63](https://img.shields.io/badge/-Pytest-0A9EDC?&logo=Pytest&logoColor=FFFFFF)
![GitHub Actions](https://img.shields.io/badge/-GitHub%20Actions-2088FF?&logo=GitHub%20Actions&logoColor=FFFFFF)

</div>

WhatYouSaid is a vectorized data hub designed to explore any topic or knowledge domain, extracting, processing, and indexing content from video, audio, and text to enable advanced semantic search and Retrieval-Augmented Generation (RAG) workflows.

This repository provides modular extractors, splitting utilities, embedding integration, and vector-store-friendly artifacts so you can build scalable, searchable profiles and knowledge bases about individuals.

---

## 📚 Documentation

Detailed guides for specific topics:

- 🐳 **[Docker Deployment Guide](docs/docker-deployment.md)**: Learn how to use Docker Profiles to run different combinations of databases (MySQL, Postgres, SQLite) and vector stores (FAISS, Weaviate).

---

## 🚀 Features

- **Multi-source extraction**: ingest data from video (YouTube), audio transcripts, and plain text sources.
- **Transcript processing and temporal splitting**: break long transcripts into semantically coherent chunks suitable for embeddings and dense retrieval.
- **Embeddings and model loader**: abstracted model loading so you can swap embedding providers easily.
- **Pluggable Vector Stores**: support for **FAISS** (local/lite), **ChromaDB** (local/server), and **Weaviate** (scalable/cloud) out of the box.
- **Pluggable SQL Databases**: support for **SQLite**, **PostgreSQL**, **MySQL**, **MariaDB**, and **MSSQL**.
- **Built for RAG**: designed to support retrieval-augmented generation workflows and semantic search over people-centric data.

---

## 🛠️ Infrastructure & Deployment

WhatYouSaid is designed to be flexible, from a lightweight local setup to a scalable production-ready environment.

### 1. Storage Options

| Component | Lightweight (Local) | Scalable / Production                                              |
| :--- | :--- |:-------------------------------------------------------------------|
| **Relational Database** | **SQLite** (Default, file-based) | **PostgreSQL**, **MySQL**, **MariaDB**, **MSSQL**                  |
| **Vector Store** | **FAISS** (Local, file-based) | **Weaviate** (Container or Cloud), **ChromaDB** (Container) |

### 2. Docker Compose Profiles

We use **Docker Profiles** to keep the environment lean. Only the services you need are started.

> 📘 **Detailed Guide**: For a step-by-step tutorial on different deployment scenarios (MySQL, Postgres, Weaviate, etc.), see our [Docker Deployment Guide](docs/docker-deployment.md).

#### **Scenario A: Lite (Default)**
Uses **SQLite** (SQL) and **FAISS** (Vector). No external database containers are started.
```bash
docker-compose up -d
```

#### **Scenario B: Scalable (Base)**
Starts **PostgreSQL** (SQL) and **Weaviate** (Vector).
```bash
# Starts Postgres and Weaviate containers
docker-compose --profile base up -d

# Note: For the backend to use these, set SQL__TYPE=postgres and VECTOR__STORE_TYPE=weaviate
```

#### **Scenario C: Custom Database**
You can mix and match services using specific profiles:
- `--profile postgres`: Starts only the PostgreSQL container.
- `--profile mysql`: Starts only the MySQL container.
- `--profile weaviate`: Starts only the Weaviate container.

**Example: Running with MySQL only**
```bash
# Start MySQL container
docker-compose --profile mysql up -d

# Run backend pointing to MySQL (local or docker)
SQL__TYPE=mysql docker-compose up -d
```

**Example: Running with Weaviate only**
```bash
# Start Weaviate container
docker-compose --profile weaviate up -d

# Run backend pointing to Weaviate
VECTOR__STORE_TYPE=weaviate docker-compose up -d
```

**Example: Running with MySQL + Weaviate**
```bash
# Start both containers
docker-compose --profile mysql --profile weaviate up -d

# Run backend pointing to both
SQL__TYPE=mysql VECTOR__STORE_TYPE=weaviate docker-compose up -d
```

### 3. Environment Variables

We use **Pydantic Settings** with double underscores (`__`) for nested configurations. 

| Category | Prefix | Examples |
| :--- | :--- | :--- |
| **Application** | `APP__` | `APP__ENV`, `APP__LIST_LOG_LEVELS` |
| **SQL Database** | `SQL__` | `SQL__TYPE`, `SQL__HOST`, `SQL__USER`, `SQL__PASSWORD` |
| **Vector Store** | `VECTOR__` | `VECTOR__STORE_TYPE`, `VECTOR__WEAVIATE_HOST`, `VECTOR__CHROMA_HOST` |
| **Embeddings** | `MODEL_EMBEDDING__` | `MODEL_EMBEDDING__NAME` |
| **Re-ranking** | `MODEL_RERANK__` | `MODEL_RERANK__NAME` |

> 💡 **Full Reference**: For a complete list of all available variables and their default values, check the [Configuration Reference in our Deployment Guide](docs/docker-deployment.md#configuration-reference).

### 4. Example `.env` file
Create a `.env` file in the root directory:
```env
# Relational DB (Choose: sqlite, postgres, mysql, mariadb, mssql)
SQL__TYPE=sqlite

# Vector Store (Choose: faiss, weaviate)
VECTOR__STORE_TYPE=faiss
VECTOR__WEAVIATE_API_KEY=your-optional-api-key

# Optional: Custom embedding model
MODEL_EMBEDDING__NAME=BAAI/bge-m3
```

---

## 💻 Local Setup (without Docker)

**Prerequisites:**
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended)

**Install with all drivers:**
```bash
# Installs core + drivers for FAISS, Weaviate, MySQL and Postgres
uv sync --all-extras
```

**Install only what you need (recommended for local development):**
```bash
# Example: Install only Postgres and Weaviate drivers
uv sync --extra postgres --extra weaviate

# Example: Install only MySQL support
uv sync --extra mysql
```

**Run tests:**
```bash
uv run pytest
```

---

## 🏗️ Architecture

- `src/infrastructure/extractors`: code to fetch raw content (e.g., YouTube transcripts, audio-to-text pipelines).
- `src/infrastructure/services`: processing and orchestration (splitting, model loading, embedding preparation).
- `src/config`: environment and settings management.
- `tests/`: unit and integration tests with coverage settings in pytest.ini.

---

## 🤝 Contributing

Contributions are welcome. Please:

- Open an issue to discuss major changes.
- Create a branch for your feature or fix, add tests, and submit a pull request.
- Keep code style consistent and run tests locally before submitting.

---

## 📄 License

This project includes a LICENSE file; see it for licensing details.

---

## 🙏 Acknowledgements

Built to be an extensible foundation for building searchable, vectorized RAG-enabled applications.

<div align="center">
    <p>Made with ❤️ by Erickson Lopes </p>

[![LinkedIn|150](https://img.shields.io/badge/LinkedIn-Erickson_Lopes-blue)](https://www.linkedin.com/in/ericksonlopes/)

</div>
