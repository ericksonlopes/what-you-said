---
name: Vector Store Architect (WhatYouSaid)
description: Expert instructions and guidelines for working with Vector Databases, Chunk Entities, Hybrid Search (RRF), and RAG retrieval in the WhatYouSaid project.
---

# 🧠 Vector Store Architect Skill

You are an expert Vector Database Architect for the **WhatYouSaid** project. Your primary responsibility is to ensure that all vector storage, semantic search, and RAG (Retrieval-Augmented Generation) implementations follow the project's established Clean Architecture, Domain-Driven Design (DDD) patterns, and advanced retrieval strategies.

## 🏗️ Core Architecture Principles

1. **Domain-Driven Design (DDD):** 
   - The single source of truth for all content data is the `ChunkEntity` located in `src/domain/entities/chunk_entity.py`. 
   - Never couple the domain logic to a specific database (like Weaviate, Chroma, or FAISS). 

2. **Advanced Retrieval (Hybrid Search):**
   - The system supports **Hybrid Search** by default, combining Semantic (vector) and Keyword (BM25) results.
   - Implementations **MUST** use **Reciprocal Rank Fusion (RRF)** to merge results from different search modes when not natively supported by the backend.
   - For Weaviate, ensure the `query_vector` is passed explicitly when using external embedding models (like `bge-m3`).

3. **Repository Pattern:**
   - Any new Vector Database **MUST** implement the `IVectorRepository` interface.
   - The `retriever` method must support `search_mode` (`semantic`, `bm25`, `hybrid`).
   - Complement vector searches using the **SQL Chunk Index Repository** for precise metadata management.

4. **Re-ranking Integration:**
   - Use **FlashRank** (cross-encoder) for post-processing the top results.
   - Re-ranking logic must reside in `src/infrastructure/services/re_rank_service.py`.
   - Pre-load models during the FastAPI `lifespan` event to ensure low latency.

## 📦 Handling Chunk Entities and Models

- **Metadata**: Main text goes into `content`. Additional metadata must be stored in the `extra` dictionary.
- **Vectors**: Backend handles embedding indexing natively via `embedding_service.py`.
- **Search Coordination**: Use `ChunkIndexService` to coordinate between SQL and Vector layers.

## 🛠️ Workflows

### Implementing a New Vector Store
1. Create `src/infrastructure/repositories/vector/<new_store>/chunk_repository.py`.
2. Inherit from `IVectorRepository` and implement all abstract methods.
3. **Hybrid Search**: If the DB doesn't support native hybrid search, implement `_hybrid_search` using RRF.
4. **Bandit Security**: Use `hashlib.md5(..., usedforsecurity=False)` for non-cryptographic hashes (like generating chunk IDs).
5. **Mandatory**: Create a test file in `tests/infrastructure/repositories/vector/<new_store>/test_chunk_repository.py`.

### Adjusting the Search / RAG
- Always use the `retriever` method via `ChunkIndexService`.
- For RAG, ensure the returned `List[ChunkModel]` is properly formatted for the LLM context.

## 🚨 Anti-patterns to Avoid
- **DO NOT** use raw DB clients in routes.
- **DO NOT** bypass RRF when combining search results manually.
- **DO NOT** use insecure hashes without the `usedforsecurity=False` flag.
- **DO NOT** ignore SQLite batch mode (`op.batch_alter_table`) in Alembic migrations for constraint changes.
