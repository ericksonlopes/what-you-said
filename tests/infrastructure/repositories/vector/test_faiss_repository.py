import pytest
from uuid import uuid4
from src.infrastructure.repositories.vector.faiss.chunk_repository import ChunkFAISSRepository
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel
from src.infrastructure.services.embeddding_service import EmbeddingService
from src.infrastructure.services.model_loader_service import ModelLoaderService

@pytest.fixture
def temp_index_path(tmp_path):
    return str(tmp_path / "faiss_test")

@pytest.fixture
def embedding_service():
    # Using a real model loader but it might be slow. 
    # For a unit test, we might want to mock it, but let's see if it works.
    loader = ModelLoaderService(model_name="BAAI/bge-m3")
    return EmbeddingService(model_loader_service=loader)

def test_faiss_repository_create_and_retrieve(temp_index_path, embedding_service):
    repo = ChunkFAISSRepository(
        embedding_service=embedding_service,
        index_path=temp_index_path,
        index_name="test_index"
    )
    
    chunk1 = ChunkModel(
        content="This is a test document about artificial intelligence.",
        job_id=uuid4(),
        content_source_id=uuid4(),
        source_type="YOUTUBE",
        embedding_model="BAAI/bge-m3"
    )
    
    chunk2 = ChunkModel(
        content="The weather today is sunny and warm.",
        job_id=uuid4(),
        content_source_id=uuid4(),
        source_type="YOUTUBE",
        embedding_model="BAAI/bge-m3"
    )
    
    # Create
    repo.create_documents([chunk1, chunk2])
    
    # Retrieve
    results = repo.retriever(query="What is the weather like?", top_kn=1)
    
    assert len(results) == 1
    assert "weather" in results[0].content
    assert results[0].id == chunk2.id

def test_faiss_repository_filtering(temp_index_path, embedding_service):
    repo = ChunkFAISSRepository(
        embedding_service=embedding_service,
        index_path=temp_index_path,
        index_name="test_index_filter"
    )
    
    subject_id = uuid4()
    chunk1 = ChunkModel(
        content="Document for subject A",
        job_id=uuid4(),
        content_source_id=uuid4(),
        source_type="YOUTUBE",
        subject_id=subject_id,
        embedding_model="BAAI/bge-m3"
    )
    
    chunk2 = ChunkModel(
        content="Document for subject B",
        job_id=uuid4(),
        content_source_id=uuid4(),
        source_type="YOUTUBE",
        subject_id=uuid4(),
        embedding_model="BAAI/bge-m3"
    )
    
    repo.create_documents([chunk1, chunk2])
    
    # Retrieve with filter
    results = repo.retriever(
        query="document", 
        top_kn=10, 
        filters={"subject_id": str(subject_id)}
    )
    
    assert len(results) == 1
    assert results[0].content == "Document for subject A"
