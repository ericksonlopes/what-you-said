from types import SimpleNamespace
from uuid import uuid4

import pytest
from src.infrastructure.repositories.vector.models.chunk_model import ChunkModel
from src.infrastructure.repositories.vector.weaviate.chunk_repository import (
    ChunkWeaviateRepository,
)


class DummyVector:
    def __init__(self):
        self.last = {}

    def add_texts(self, texts, metadatas, ids):
        self.last["texts"] = texts
        self.last["metadatas"] = metadatas
        self.last["ids"] = ids
        return [str(u) for u in ids]


class DummyVectorCtx:
    def __init__(self, vector):
        self._vector = vector

    def __enter__(self):
        return self._vector

    def __exit__(self, exc_type, exc, tb):
        return False


class DummyRetriever:
    def __init__(self, docs):
        self._docs = docs

    def invoke(self, q):
        return self._docs


class DummyClientCtx:
    def __init__(self, response):
        self._response = response

    def __enter__(self):
        class Collection:
            def __init__(self, response):
                self._response = response
                self.query = SimpleNamespace(
                    fetch_objects=lambda **kwargs: self._response
                )
                self.data = SimpleNamespace(
                    delete_many=lambda where: SimpleNamespace(matches=1)
                )

            def get(self, _):
                return self

        self.collections = Collection(self._response)
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def make_repo():
    # supply dummy objects; we'll override vector_store in tests
    repo = ChunkWeaviateRepository(
        weaviate_client=DummyClientCtx(None),
        embedding_service=object(),
        collection_name="c",
    )
    return repo


@pytest.mark.ChunkRepository
class TestChunkRepository:
    def test_create_documents_success(self, monkeypatch):
        repo = make_repo()
        vec = DummyVector()
        repo.vector_store = DummyVectorCtx(vec)

        doc = ChunkModel(
            job_id=uuid4(),
            content_source_id=uuid4(),
            source_type="youtube",
            external_source="v1",
            subject_id=uuid4(),
            embedding_model="models-x",
            content="hello",
        )
        created = repo.create_documents([doc])
        assert isinstance(created, list)
        assert "texts" in vec.last
        assert vec.last["texts"] == ["hello"]
        assert isinstance(vec.last["ids"][0], type(doc.id))

    def test_create_documents_invalid_texts(self, monkeypatch):
        repo = make_repo()
        vec = DummyVector()
        repo.vector_store = DummyVectorCtx(vec)

        # invalid content (not a string)
        class FakeDoc:
            def __init__(self):
                self.id = uuid4()
                self.content = 123  # non-string to trigger ValueError

            def model_dump(self, exclude=None):
                return {
                    "id": self.id,
                    "job_id": uuid4(),
                    "content_source_id": uuid4(),
                    "source_type": "youtube",
                    "external_source": "v1",
                    "subject_id": uuid4(),
                    "embedding_model": "m",
                    "content": self.content,
                }

        bad = FakeDoc()
        with pytest.raises(ValueError):
            repo.create_documents([bad])

    def test_retriever_returns_models(self, monkeypatch):
        repo = make_repo()

        # stub retriever to return Document-like objects with score
        doc = SimpleNamespace(
            page_content="hi",
            metadata={
                "source_type": "youtube",
                "external_source": "v1",
                "subject_id": str(uuid4()),
                "embedding_model": "m",
                "job_id": str(uuid4()),
                "content_source_id": str(uuid4()),
            },
        )
        docs_with_scores = [(doc, float(0.9))]

        class FakeVectorStore:
            def similarity_search_with_score(self, query, k, filters=None):
                return docs_with_scores

        repo.vector_store = DummyVectorCtx(FakeVectorStore())
        results = repo.retriever(query="q", top_kn=2)
        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(results[0], ChunkModel)
        assert results[0].score == float(0.9)

    def test_list_chunks_and_delete(self, monkeypatch):
        # prepare fake response object with objects
        obj = SimpleNamespace(
            uuid=str(uuid4()),
            properties={
                "content": "txt",
                "job_id": str(uuid4()),
                "content_source_id": str(uuid4()),
                "source_type": "youtube",
                "external_source": "v1",
                "subject_id": str(uuid4()),
                "embedding_model": "m",
            },
        )
        response = SimpleNamespace(objects=[obj])
        repo = ChunkWeaviateRepository(
            weaviate_client=DummyClientCtx(response),
            embedding_service=object(),
            collection_name="c",
        )

        chunks = repo.list_chunks(filters=None)
        assert isinstance(chunks, list)
        assert len(chunks) == 1
        assert isinstance(chunks[0], ChunkModel)

        # delete uses the client context and returns matches
        deleted = repo.delete(filters=None)
        assert deleted == 1
