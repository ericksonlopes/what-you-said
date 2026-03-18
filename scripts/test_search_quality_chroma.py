import uuid
from src.config.settings import VectorConfig
from src.infrastructure.repositories.vector.chroma.chunk_repository import (
    ChunkChromaRepository,
)
from src.infrastructure.services.embedding_service import EmbeddingService
from src.infrastructure.services.model_loader_service import ModelLoaderService
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel
from src.domain.entities.enums.search_mode_enum import SearchMode


def test_search_engines_chroma():
    print("🔍 Starting Search Quality Test (ChromaDB)...")

    # Configuration to connect to local container
    cfg = VectorConfig(
        chroma_host="localhost", chroma_port=8000, collection_name_chunks="test_chunks"
    )

    # Initialize real services
    model_name = "BAAI/bge-m3"
    model_loader = ModelLoaderService(model_name=model_name)
    embedding_service = EmbeddingService(model_loader_service=model_loader)

    repo = ChunkChromaRepository(
        embedding_service=embedding_service,
        host=cfg.chroma_host,
        port=cfg.chroma_port,
        collection_name=cfg.collection_name_chunks,
    )

    # Note: We won't delete all to avoid potential issues with empty collections,
    # instead we use unique source_ids to filter or just append.

    # Unique IDs for this test to avoid collisions
    job_id = uuid.uuid4()
    source_id = uuid.uuid4()
    subject_id = uuid.uuid4()

    # 1. Preparing test data
    documents = [
        ChunkModel(
            id=uuid.uuid4(),
            job_id=job_id,
            content_source_id=source_id,
            subject_id=subject_id,
            embedding_model=model_name,
            content="Space exploration requires advanced rockets and orbital mechanics.",
            external_source="space_news",
            source_type="text",
        ),
        ChunkModel(
            id=uuid.uuid4(),
            job_id=job_id,
            content_source_id=source_id,
            subject_id=subject_id,
            embedding_model=model_name,
            content="The new electric car battery offers a range of 500 miles on a single charge.",
            external_source="auto_blog",
            source_type="text",
        ),
        ChunkModel(
            id=uuid.uuid4(),
            job_id=job_id,
            content_source_id=source_id,
            subject_id=subject_id,
            embedding_model=model_name,
            content="NASA's new lunar rover battery relies on orbital mechanics for charging.",
            external_source="hybrid_source",
            source_type="text",
        ),
    ]

    print(f"📦 Indexing {len(documents)} documents in ChromaDB...")
    repo.create_documents(documents)

    # Use filter to only search among newly inserted docs
    test_filter = {"content_source_id": str(source_id)}

    # --- TEST 1: SEMANTIC ---
    print("\n--- Test 1: Semantic Search ---")
    query_semantic = "vehicles and power"
    results = repo.retriever(
        query_semantic, top_kn=2, search_mode=SearchMode.SEMANTIC, filters=test_filter
    )
    print(f"Query: '{query_semantic}'")
    for i, r in enumerate(results):
        print(f"  [{i + 1}] Score: {r.score:.4f} | Content: {r.content[:50]}...")

    # --- TEST 2: BM25 (KEYWORD) ---
    print("\n--- Test 2: BM25 Search (Keyword) ---")
    query_keyword = "lunar"
    results = repo.retriever(
        query_keyword, top_kn=1, search_mode=SearchMode.BM25, filters=test_filter
    )
    print(f"Query: '{query_keyword}'")
    if results:
        print(f"  [OK] Found: {results[0].content[:50]}...")
    else:
        print("  [ERROR] Nothing found for 'lunar'")

    # --- TEST 3: HYBRID ---
    print("\n--- Test 3: Hybrid Search (Semantic + BM25 RRF) ---")
    query_hybrid = "rocket battery"
    results = repo.retriever(
        query_hybrid, top_kn=2, search_mode=SearchMode.HYBRID, filters=test_filter
    )
    print(f"Query: '{query_hybrid}'")
    for i, r in enumerate(results):
        print(f"  [{i + 1}] RRF Score: {r.score:.4f} | Content: {r.content[:50]}...")

    print("\n✅ Test completed successfully!")


if __name__ == "__main__":
    test_search_engines_chroma()
