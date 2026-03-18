# 🐳 Docker Deployment Guide

WhatYouSaid uses **Docker Profiles** to allow a modular and lightweight infrastructure. Instead of starting every service at once, you can choose exactly which database and vector store you want to run.

---

## 🏗️ Execution Strategies

The project supports three main components:
1.  **Backend & Frontend**: Always required.
2.  **SQL Database**: Choose between `SQLite` (default), `PostgreSQL`, `MySQL`, `MariaDB`, or `MSSQL`.
3.  **Vector Store**: Choose between `FAISS` (default), `Weaviate`, or `ChromaDB`.

### 1. Scenario: Lightweight (Default)
**Stack**: SQLite (SQL) + FAISS (Vector)
- **Best for**: Local development, low resources.
- **Why**: No extra containers are needed. Everything is stored in local files.

```bash
docker-compose up -d
```

---

### 2. Scenario: Scalable (Base)
**Stack**: PostgreSQL (SQL) + Weaviate (Vector)
- **Best for**: Large datasets, persistent services.
- **Why**: PostgreSQL handles heavy relational data better, and Weaviate allows for scalable semantic search.

```bash
# Start the containers
docker-compose --profile base up -d

# Override settings to use these services
SQL__TYPE=postgres VECTOR__STORE_TYPE=weaviate docker-compose up -d
```

---

### 3. Scenario: MySQL / MariaDB Focused
**Stack**: MySQL or MariaDB + FAISS
- **Best for**: Environments where MySQL/MariaDB is the standard.

```bash
# Start MySQL container
docker-compose --profile mysql up -d

# Run backend pointing to MySQL (local or docker)
SQL__TYPE=mysql docker-compose up -d
```

---

### 4. Scenario: Vector Focused (Cloud Native)
**Stack**: SQLite + Weaviate
- **Best for**: When you want a scalable vector store but keep the relational data simple.

```bash
# Start Weaviate container
docker-compose --profile weaviate up -d

# Override settings to use Weaviate
VECTOR__STORE_TYPE=weaviate docker-compose up -d
```

---

### 5. Scenario: Enterprise Stack
**Stack**: MSSQL + FAISS
- **Best for**: Corporate environments using SQL Server.

```bash
# Start MSSQL container
docker-compose --profile mssql up -d

# Override settings
SQL__TYPE=mssql SQL__PASSWORD=YourSecurePassword123! docker-compose up
```

---

### 6. Scenario: Custom Mix (Hybrid)
You can combine specific profiles. For example, if you want **MySQL** for data but **Weaviate** for vectors:

```bash
# Start both containers
docker-compose --profile mysql --profile weaviate up -d

# Run backend pointing to both (local or docker)
SQL__TYPE=mysql VECTOR__STORE_TYPE=weaviate docker-compose up -d
```

---

## 🐳 Automated Environment Setup

Our Docker image is intelligent. It detects your `SQL__TYPE` and `VECTOR__STORE_TYPE` environment variables and automatically installs the necessary drivers using `uv` during startup.

This keeps the image small and ensures you only run the code you actually need.

---

---

## ⚙️ Configuration Reference

WhatYouSaid uses **Pydantic Settings** to manage configurations. When using environment variables or a `.env` file, use the double underscore (`__`) as a delimiter for nested settings.

### 1. Application Settings (`APP__`)
| Variable | Default | Description |
| :--- | :--- | :--- |
| `APP__ENV` | `development` | Environment mode (`development`, `production`, `testing`). |
| `APP__LIST_LOG_LEVELS` | `INFO,WARNING,ERROR` | Comma-separated list of log levels to show. |

### 2. SQL Database Settings (`SQL__`)
Required if using any database other than SQLite.
| Variable | Options | Description |
| :--- | :--- | :--- |
| `SQL__TYPE` | `sqlite`, `postgres`, `mysql`, `mariadb`, `mssql` | The database dialect. |
| `SQL__HOST` | (string) | Hostname of the database server. |
| `SQL__PORT` | (int) | Port of the database server. |
| `SQL__USER` | (string) | Username for authentication. |
| `SQL__PASSWORD` | (string) | Password for authentication. |
| `SQL__DATABASE` | (string) | Database name to connect to. |

### 3. Vector Store Settings (`VECTOR__`)
| Variable | Default | Description |
| :--- | :--- | :--- |
| `VECTOR__STORE_TYPE` | `faiss` | Choice between `faiss`, `weaviate`, or `chroma`. |
| `VECTOR__VECTOR_INDEX_PATH` | `./vector_index` | Local path for FAISS index files. |
| `VECTOR__WEAVIATE_HOST` | `localhost` | Weaviate server hostname. |
| `VECTOR__WEAVIATE_PORT` | `8081` | Weaviate HTTP port. |
| `VECTOR__WEAVIATE_API_KEY` | `******` | Optional API key for Weaviate authentication. |
| `VECTOR__WEAVIATE_GRPC_PORT` | `50051` | Weaviate gRPC port. |
| `VECTOR__CHROMA_HOST` | `localhost` | ChromaDB server hostname. |
| `VECTOR__CHROMA_PORT` | `8000` | ChromaDB port. |

### 4. Model Settings (`MODEL_EMBEDDING__`)
| Variable | Default | Description |
| :--- | :--- | :--- |
| `MODEL_EMBEDDING__NAME` | `BAAI/bge-m3` | The HuggingFace model name for embeddings. |

---

## 📄 Example `.env` File

Create a `.env` file in the root directory to manage your settings easily:

```env
# Database (Postgres Example)
SQL__TYPE=postgres
SQL__HOST=localhost
SQL__PORT=5432
SQL__USER=myuser
SQL__PASSWORD=mypassword
SQL__DATABASE=whatyousaid

# Vector Store (ChromaDB Example)
VECTOR__STORE_TYPE=chroma
VECTOR__CHROMA_HOST=localhost
VECTOR__CHROMA_PORT=8000

# Logs
APP__LIST_LOG_LEVELS=DEBUG,INFO,WARNING,ERROR
```

---

## 🛠️ Handy Commands

**Check which profiles are active:**
```bash
docker-compose config --profiles
```

**Stop everything and clean volumes:**
```bash
docker-compose --profile base down -v
```

**View logs for a specific service:**
```bash
docker-compose logs -f backend
```
