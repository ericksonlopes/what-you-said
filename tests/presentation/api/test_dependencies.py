import pytest
from unittest.mock import MagicMock, patch
from src.presentation.api.dependencies import (
    get_settings,
    get_chunk_repo,
    get_source_repo,
    get_job_repo,
    get_subject_repo,
    get_model_loader,
    get_embedding_service,
    get_weaviate_client,
    get_vector_repository,
    get_ks_service,
    get_cs_service,
    get_job_service,
    get_chunk_vector_service,
    get_chunk_index_service,
    get_youtube_vector_service,
    get_search_chunks_use_case,
    get_ingest_youtube_use_case,
)
from src.config.settings import Settings
from src.domain.entities.enums.vector_store_type_enum import VectorStoreType


@pytest.mark.Dependencies
class TestDependencies:
    def test_get_settings(self):
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_repositories(self):
        assert get_chunk_repo() is not None
        assert get_source_repo() is not None
        assert get_job_repo() is not None
        assert get_subject_repo() is not None

    def test_get_model_loader(self):
        settings = MagicMock()
        settings.model_embedding.name = "test-model"
        with patch(
            "src.infrastructure.services.model_loader_service.SentenceTransformer"
        ):
            loader = get_model_loader(settings)
            assert loader is not None

    def test_get_embedding_service(self):
        loader = MagicMock()
        svc = get_embedding_service(loader)
        assert svc is not None

    def test_get_weaviate_client(self):
        settings = MagicMock()
        with patch(
            "src.infrastructure.repositories.vector.weaviate.weaviate_client.WeaviateClient"
        ) as _:
            client = get_weaviate_client(settings)
            assert client is not None

    def test_get_vector_repository_weaviate(self):
        settings = MagicMock()
        settings.vector.store_type = VectorStoreType.WEAVIATE
        settings.vector.collection_name_chunks = "test_collection"
        loader = MagicMock()

        with (
            patch(
                "src.infrastructure.repositories.vector.weaviate.weaviate_client.WeaviateClient"
            ),
            patch(
                "src.infrastructure.repositories.vector.weaviate.chunk_repository.ChunkWeaviateRepository"
            ),
        ):
            repo = get_vector_repository(settings, loader)
            assert repo is not None

    def test_get_vector_repository_chroma(self):
        settings = MagicMock()
        settings.vector.store_type = VectorStoreType.CHROMA
        settings.vector.chroma_host = "test"
        settings.vector.chroma_port = 8000
        settings.vector.collection_name_chunks = "test_collection"
        loader = MagicMock()

        with patch(
            "src.infrastructure.repositories.vector.chroma.chunk_repository.ChunkChromaRepository"
        ):
            repo = get_vector_repository(settings, loader)
            assert repo is not None

    def test_get_vector_repository_faiss(self):
        settings = MagicMock()
        settings.vector.store_type = VectorStoreType.FAISS
        settings.vector.vector_index_path = "test_path"
        loader = MagicMock()

        with patch(
            "src.infrastructure.repositories.vector.faiss.chunk_repository.ChunkFAISSRepository"
        ):
            repo = get_vector_repository(settings, loader)
            assert repo is not None

    def test_get_vector_repository_unsupported(self):
        settings = MagicMock()
        settings.vector.store_type = "UNSUPPORTED"
        loader = MagicMock()
        with pytest.raises(ValueError, match="Unsupported vector store type"):
            get_vector_repository(settings, loader)

    def test_services(self):
        mock_repo = MagicMock()
        assert get_ks_service(mock_repo) is not None
        assert get_cs_service(mock_repo) is not None
        assert get_job_service(mock_repo) is not None
        assert get_chunk_index_service(mock_repo) is not None

    def test_get_chunk_vector_service(self):
        mock_repo = MagicMock()
        svc = get_chunk_vector_service(mock_repo)
        assert svc is not None

    def test_get_youtube_vector_service(self):
        mock_repo = MagicMock()
        svc = get_youtube_vector_service(mock_repo)
        assert svc is not None

    def test_get_search_chunks_use_case(self):
        mock_vector_svc = MagicMock()
        mock_ks_svc = MagicMock()
        uc = get_search_chunks_use_case(mock_vector_svc, mock_ks_svc)
        assert uc is not None

    def test_get_ingest_youtube_use_case(self):
        kwargs = {
            "ks_svc": MagicMock(),
            "cs_svc": MagicMock(),
            "job_svc": MagicMock(),
            "model_loader": MagicMock(),
            "embed_svc": MagicMock(),
            "chunk_svc": MagicMock(),
            "yt_vector_svc": MagicMock(),
            "settings": MagicMock(),
        }
        kwargs["settings"].vector.store_type = VectorStoreType.FAISS
        uc = get_ingest_youtube_use_case(**kwargs)
        assert uc is not None
