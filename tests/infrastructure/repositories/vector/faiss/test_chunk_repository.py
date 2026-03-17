import pytest
import sys
from uuid import uuid4
from unittest.mock import MagicMock, patch
from src.infrastructure.repositories.vector.faiss.chunk_repository import ChunkFAISSRepository
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel
from src.infrastructure.services.embedding_service import EmbeddingService
from src.infrastructure.services.model_loader_service import ModelLoaderService

@pytest.fixture
def temp_index_path(tmp_path):
    return str(tmp_path / "faiss_test")

@pytest.fixture
def embedding_service():
    loader = ModelLoaderService(model_name="BAAI/bge-m3")
    return EmbeddingService(model_loader_service=loader)

@pytest.fixture(autouse=True)
def mock_faiss(monkeypatch):
    """Mock faiss and langchain_community.vectorstores.faiss"""
    mock_faiss_mod = MagicMock()
    monkeypatch.setitem(sys.modules, "faiss", mock_faiss_mod)
    
    class FakeFAISS:
        def __init__(self):
            self.docs = []
            self.ids = []
            self.docstore = MagicMock()
            self.docstore._dict = {}

        @classmethod
        def from_texts(cls, texts, embedding, metadatas=None, ids=None, **kwargs):
            instance = cls()
            instance.add_texts(texts, metadatas, ids)
            return instance

        def add_texts(self, texts, metadatas=None, ids=None, **kwargs):
            new_ids = []
            for i, text in enumerate(texts):
                doc = MagicMock()
                doc.page_content = text
                doc.metadata = (metadatas[i] if metadatas else {}).copy()
                doc_id = str(ids[i]) if ids else str(uuid4())
                doc.id = doc_id
                doc.metadata["id"] = doc_id
                self.docs.append(doc)
                self.ids.append(doc_id)
                self.docstore._dict[doc_id] = doc
                new_ids.append(doc_id)
            return new_ids

        def similarity_search_with_score(self, query, k=5, filter=None, **kwargs):
            results = []
            # Simple keyword matching for mock
            matching_docs = []
            stop_words = {"what", "is", "the", "a", "an", "this", "about"}
            query_words = {word for word in query.lower().replace("?", "").split() if word not in stop_words}
            
            for doc in self.docs:
                if filter and not filter(doc.metadata):
                    continue
                
                content_lower = doc.page_content.lower()
                # If no meaningful query words, just use a default score
                if not query_words:
                    matching_docs.append((doc, 0.5))
                    continue

                if any(word in content_lower for word in query_words):
                    matching_docs.append((doc, 0.1)) # better score for matches
                else:
                    matching_docs.append((doc, 0.9)) # worse score
            
            # Sort by score
            matching_docs.sort(key=lambda x: x[1])
            return matching_docs[:k]

        def delete(self, ids):
            for doc_id in ids:
                if doc_id in self.docstore._dict:
                    doc = self.docstore._dict.pop(doc_id)
                    if doc in self.docs:
                        self.docs.remove(doc)
                    if doc_id in self.ids:
                        self.ids.remove(doc_id)
            return True

        def save_local(self, folder_path, index_name="index"):
            pass

        @classmethod
        def load_local(cls, folder_path, embeddings, index_name="index", allow_dangerous_deserialization=False):
            return cls()

    mock_lc_faiss = MagicMock()
    mock_lc_faiss.FAISS = FakeFAISS
    monkeypatch.setitem(sys.modules, "langchain_community.vectorstores", mock_lc_faiss)
    monkeypatch.setitem(sys.modules, "langchain_community.vectorstores.faiss", mock_lc_faiss)
    return FakeFAISS

def test_faiss_repository_create_and_retrieve(temp_index_path, embedding_service, mock_faiss):
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
        external_source="source1",
        subject_id=uuid4(),
        embedding_model="BAAI/bge-m3"
    )
    
    chunk2 = ChunkModel(
        content="The weather today is sunny and warm.",
        job_id=uuid4(),
        content_source_id=uuid4(),
        source_type="YOUTUBE",
        external_source="source2",
        subject_id=uuid4(),
        embedding_model="BAAI/bge-m3"
    )
    
    # Create
    repo.create_documents([chunk1, chunk2])
    
    # Retrieve
    results = repo.retriever(query="What is the weather like?", top_kn=1)
    
    assert len(results) == 1
    assert "weather" in results[0].content
    assert str(results[0].id) == str(chunk2.id)

def test_faiss_repository_filtering(temp_index_path, embedding_service, mock_faiss):
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
        external_source="sourceA",
        subject_id=subject_id,
        embedding_model="BAAI/bge-m3"
    )
    
    chunk2 = ChunkModel(
        content="Document for subject B",
        job_id=uuid4(),
        content_source_id=uuid4(),
        source_type="YOUTUBE",
        external_source="sourceB",
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

def test_faiss_repository_delete(temp_index_path, embedding_service, mock_faiss):
    repo = ChunkFAISSRepository(
        embedding_service=embedding_service,
        index_path=temp_index_path,
        index_name="test_delete"
    )
    
    chunk_id = uuid4()
    chunk = ChunkModel(
        id=chunk_id,
        content="Delete me",
        job_id=uuid4(),
        content_source_id=uuid4(),
        source_type="YOUTUBE",
        external_source="source_del",
        subject_id=uuid4(),
        embedding_model="BAAI/bge-m3"
    )
    
    repo.create_documents([chunk])
    assert repo.is_ready() is True
    
    # List before delete
    chunks = repo.list_chunks(filters={"external_source": "source_del"})
    assert len(chunks) == 1
    
    # Delete by ID
    deleted_count = repo.delete(filters={"id": str(chunk_id)})
    assert deleted_count == 1
    
    # List after delete
    chunks = repo.list_chunks(filters={"external_source": "source_del"})
    assert len(chunks) == 0

def test_faiss_repository_delete_with_general_filter(temp_index_path, embedding_service, mock_faiss):
    repo = ChunkFAISSRepository(
        embedding_service=embedding_service,
        index_path=temp_index_path,
        index_name="test_delete_filter"
    )
    
    chunk = ChunkModel(
        content="Delete me",
        job_id=uuid4(),
        content_source_id=uuid4(),
        source_type="YOUTUBE",
        external_source="source_del_filter",
        subject_id=uuid4(),
        embedding_model="BAAI/bge-m3"
    )
    
    repo.create_documents([chunk])
    
    # Delete by external_source
    deleted_count = repo.delete(filters={"external_source": "source_del_filter"})
    assert deleted_count == 1
    
    chunks = repo.list_chunks(filters={"external_source": "source_del_filter"})
    assert len(chunks) == 0

def test_faiss_repository_delete_no_filters_skips(temp_index_path, embedding_service, mock_faiss):
    repo = ChunkFAISSRepository(
        embedding_service=embedding_service,
        index_path=temp_index_path,
        index_name="test_delete_no_filter"
    )
    repo.create_documents([ChunkModel(content="test", job_id=uuid4(), content_source_id=uuid4(), source_type="YOUTUBE", external_source="s", subject_id=uuid4(), embedding_model="m")])
    
    deleted_count = repo.delete(filters=None)
    assert deleted_count == 0

def test_faiss_repository_initialization_existing_index(temp_index_path, embedding_service, mock_faiss):
    # First create and save
    repo1 = ChunkFAISSRepository(
        embedding_service=embedding_service,
        index_path=temp_index_path,
        index_name="test_existing"
    )
    repo1.create_documents([ChunkModel(content="test", job_id=uuid4(), content_source_id=uuid4(), source_type="YOUTUBE", external_source="s", subject_id=uuid4(), embedding_model="m")])
    
    # Mock os.path.exists to return True for the index file
    with patch("os.path.exists", return_value=True):
        repo2 = ChunkFAISSRepository(
            embedding_service=embedding_service,
            index_path=temp_index_path,
            index_name="test_existing"
        )
        assert repo2.is_ready() is True

def test_faiss_repository_error_handling(temp_index_path, embedding_service, mock_faiss):
    repo = ChunkFAISSRepository(
        embedding_service=embedding_service,
        index_path=temp_index_path,
        index_name="test_errors"
    )
    
    # Error in create_documents
    with patch.object(repo, "_save", side_effect=Exception("Save failed")):
        with pytest.raises(Exception) as excinfo:
            repo.create_documents([ChunkModel(content="test", job_id=uuid4(), content_source_id=uuid4(), source_type="YOUTUBE", external_source="s", subject_id=uuid4(), embedding_model="m")])
        assert "Save failed" in str(excinfo.value)

    # Error in retriever
    repo.create_documents([ChunkModel(content="test", job_id=uuid4(), content_source_id=uuid4(), source_type="YOUTUBE", external_source="s", subject_id=uuid4(), embedding_model="m")])
    with patch.object(repo._vector_store, "similarity_search_with_score", side_effect=Exception("Search failed")):
        with pytest.raises(Exception) as excinfo:
            repo.retriever(query="test")
        assert "Search failed" in str(excinfo.value)

    # Error in delete
    with patch.object(repo._vector_store, "delete", side_effect=Exception("Delete failed")):
        with pytest.raises(Exception) as excinfo:
            repo.delete(filters={"id": "something"})
        assert "Delete failed" in str(excinfo.value)

    # Error in list_chunks
    with patch("src.domain.mappers.chunk_mapper.ChunkMapper.document_to_model", side_effect=Exception("Map failed")):
        with pytest.raises(Exception) as excinfo:
            repo.list_chunks(filters={})
        assert "Map failed" in str(excinfo.value)

def test_faiss_repository_load_error(temp_index_path, embedding_service, mock_faiss):
    with patch("os.path.exists", return_value=True):
        with patch("langchain_community.vectorstores.FAISS.load_local", side_effect=Exception("Load failed")):
            repo = ChunkFAISSRepository(
                embedding_service=embedding_service,
                index_path=temp_index_path,
                index_name="test_load_error"
            )
            assert repo.is_ready() is False

def test_faiss_repository_retriever_no_store(temp_index_path, embedding_service):
    # No mock_faiss to simulate no vector store
    repo = ChunkFAISSRepository(
        embedding_service=embedding_service,
        index_path=temp_index_path,
        index_name="test_no_store"
    )
    assert repo.retriever("query") == []
    assert repo.list_chunks({}) == []
    assert repo.delete({"id": "1"}) == 0
