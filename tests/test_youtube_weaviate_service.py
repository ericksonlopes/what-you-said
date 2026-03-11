import pytest
from uuid import uuid4

from src.infrastructure.services.youtube_weaviate_service import YouTubeService
from src.domain.entities.chunk_entity import ChunkEntity
from src.domain.entities.external_source_enum_entity import ExternalSourceEnum
from src.infrastructure.repository.weaviate.model.chunk_model import ChunkModel


class DummyRepo:
    def __init__(self):
        self.last_created = None

    def create_documents(self, lista):
        self.last_created = lista
        return ["id1"]

    def retriever(self, query, top_kn=5, filters=None):
        # return list of ChunkModel
        return [ChunkModel(job_id=uuid4(), content_source_id=uuid4(), source_type="youtube", external_source="v1", subject_id=uuid4(), embedding_model="m", content="abc")]

    def list_chunks(self, filters=None):
        return [ChunkModel(job_id=uuid4(), content_source_id=uuid4(), source_type="youtube", external_source="v1", subject_id=uuid4(), embedding_model="m", content="abc")]

    def delete(self, filters=None):
        return 2


def make_chunk_entity():
    return ChunkEntity(
        id=uuid4(),
        job_id=uuid4(),
        content_source_id=uuid4(),
        source_type=ExternalSourceEnum.YOUTUBE,
        external_source="vid",
        content="x",
    )


@pytest.mark.YoutubeWeaviateService
class TestYouTubeWeaviateService:
    def test_index_documents_and_search(self):
        repo = DummyRepo()
        service = YouTubeService(repository=repo)
        entity = make_chunk_entity()
        created = service.index_documents([entity])
        assert created == ["id1"]

        # search with empty query raises
        with pytest.raises(ValueError):
            service.search(query="", top_k=1)

        res = service.search(query="q", top_k=1)
        assert isinstance(res, list)
        assert len(res) == 1

    def test_search_by_video_id_and_delete(self):
        repo = DummyRepo()
        service = YouTubeService(repository=repo)

        with pytest.raises(ValueError):
            service.search_by_video_id(video_id="")

        results = service.search_by_video_id(video_id="vid")
        assert isinstance(results, list)
        assert len(results) == 1

        with pytest.raises(ValueError):
            service.delete_by_video_id("")

        deleted = service.delete_by_video_id(video_id="vid")
        assert deleted == 2
