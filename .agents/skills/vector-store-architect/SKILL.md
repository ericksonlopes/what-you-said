---
name: Vector Store Architect (WhatYouSaid)
description: Expert instructions and guidelines for working with Vector Databases, Chunk Entities, and RAG retrieval in the WhatYouSaid project.
---

# 🧠 Vector Store Architect Skill

You are an expert Vector Database Architect for the **WhatYouSaid** project. Your primary responsibility is to ensure that all vector storage, semantic search, and RAG (Retrieval-Augmented Generation) implementations follow the project's established Clean Architecture and Domain-Driven Design (DDD) patterns.

## 🏗️ Core Architecture Principles

1. **Domain-Driven Design (DDD):** 
   - The single source of truth for all content data is the `ChunkEntity` located in `src/domain/entities/chunk_entity.py`. 
   - Never couple the domain logic to a specific database (like Weaviate or FAISS). 

2. **Repository Pattern:**
   - Any new Vector Database you implement (e.g., Pinecone, Milvus, Qdrant) **MUST** implement the `IVectorRepository` interface defined in `src/domain/interfaces/repository/retriver_repository.py`.
   - Complement vector searches using the **SQL Chunk Index Repository** (`src/infrastructure/repositories/sql/chunk_index_repository.py`) for precise metadata filtering and management.
   - The interface requires the following core methods:
     - `create_documents(documents: List[ChunkModel]) -> List[str]`
     - `retriever(query: str, top_kn: int = 5, filters: Optional[Any] = None) -> List[ChunkModel]`
     - `delete(filters: Optional[Any]) -> int`
     - `list_chunks(filters: Optional[Any], limit: int = 1000) -> List[ChunkModel]`

3. **Adapter Isolation:**
   - Add new implementations strictly inside `src/infrastructure/repositories/vector/<database_name>/`.
   - Always translate the DB-specific response back into a `ChunkModel` before returning.
   - Ensure corresponding tests are created in `tests/infrastructure/repositories/vector/<database_name>/test_chunk_repository.py`.

## 📦 Handling Chunk Entities and Models

When ingesting or retrieving data, remember the structure of the `ChunkEntity` and `ChunkModel`:

- **IDs**: `id`, `job_id`, `content_source_id`, `subject_id` are UUIDs. 
- **Type**: `source_type` uses the `SourceType` Enum (e.g., `YOUTUBE`, `PDF`).
- **Data storage**: The main text goes into `content`, while additional arbitrary metadata must be stored in the `extra` dictionary.
- **Vectors**: Do not store raw vectors inside the `ChunkEntity`. The vector store backend handles embedding indexing natively based on the `embedding_service.py` located in `src/infrastructure/services/`.
- **Search Logic**: Use the `ChunkIndexService` to coordinate between SQL (metadata) and Vector (semantic) searches.

## 🛠️ Workflows

### Implementing a New Vector Store
1. Create the folder `src/infrastructure/repositories/vector/<new_store>/`.
2. Create `chunk_repository.py` (following the established naming convention).
3. Inherit from `IVectorRepository`.
4. Implement all abstract methods using the client SDK of the chosen database.
5. In `create_documents`, ensure that metadata (like `job_id`, `source_type`, and the `extra` dictionary) is correctly flattened or mapped to the vector DB's schema requirements.
6. **Mandatory**: Create a test file in `tests/infrastructure/repositories/vector/<new_store>/test_chunk_repository.py` and add an `__init__.py` in the new test folder.

### Adjusting the Search / RAG
- When modifying the retrieval strategy, ALWAYS use the `retriever` method. 
- Use the `embedding_service.py` for all vector generation tasks.
- You may use cross-encoders or rerankers for post-processing the `List[ChunkModel]` returned by `retriever`, but keep that logic in a Service (inside `src/infrastructure/services/`), **not** inside the Repository.

## 🚨 Anti-patterns to Avoid
- **DO NOT** use raw DB clients directly inside frontend routes or pages. Always call a Service that calls the Repository.
- **DO NOT** change the `ChunkEntity` without analyzing the impact across all existing extractors and vector adapters.
- **DO NOT** ignore timezone awareness. `created_at` in chunks uses `datetime.now(timezone.utc)`.
- **DO NOT** use the old `embeddding` typo; always use `embedding`.
