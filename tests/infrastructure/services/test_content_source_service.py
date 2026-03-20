import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from datetime import datetime, timezone
from types import SimpleNamespace
from src.infrastructure.services.content_source_service import ContentSourceService
from src.domain.entities.enums.content_source_status_enum import ContentSourceStatus
from src.domain.entities.enums.source_type_enum_entity import SourceType


@pytest.mark.Dependencies
class TestContentSourceService:
    @pytest.fixture
    def mock_repo(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_repo):
        return ContentSourceService(repository=mock_repo)

    def create_mock_model(self, **kwargs):
        cid = kwargs.get("id", uuid4())
        return SimpleNamespace(
            id=cid,
            subject_id=kwargs.get("subject_id", uuid4()),
            source_type=kwargs.get("source_type", "youtube"),
            external_source=kwargs.get("external_source", "ext"),
            title=kwargs.get("title", "Title"),
            language=kwargs.get("language", "en"),
            status=kwargs.get("status", "active"),
            processing_status=kwargs.get("processing_status", "done"),
            embedding_model=kwargs.get("embedding_model", "emb"),
            dimensions=kwargs.get("dimensions", 384),
            chunks=kwargs.get("chunks", 10),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def test_create_source(self, service, mock_repo):
        sid = uuid4()
        cid = uuid4()
        mock_repo.create.return_value = cid
        mock_repo.get_by_id.return_value = self.create_mock_model(
            id=cid, subject_id=sid
        )

        res = service.create_source(
            subject_id=sid,
            source_type=SourceType.YOUTUBE,
            external_source="vid",
            status=ContentSourceStatus.DONE,
            title="T",
        )

        assert res.id == cid
        mock_repo.create.assert_called_once()

    def test_get_by_source_info(self, service, mock_repo):
        model = self.create_mock_model()
        mock_repo.get_by_source_info.return_value = [model]

        res = service.get_by_source_info(SourceType.YOUTUBE, "vid")
        assert res.id == model.id

        mock_repo.get_by_source_info.return_value = []
        assert service.get_by_source_info(SourceType.YOUTUBE, "none") is None

    def test_get_by_id(self, service, mock_repo):
        model = self.create_mock_model()
        mock_repo.get_by_id.return_value = model
        res = service.get_by_id(model.id)
        assert res.id == model.id

    def test_list_by_subject(self, service, mock_repo):
        mock_repo.list_by_subject.return_value = [self.create_mock_model()]
        res = service.list_by_subject(uuid4())
        assert len(res) == 1

    def test_list_all(self, service, mock_repo):
        mock_repo.list.return_value = [self.create_mock_model()]
        res = service.list_all()
        assert len(res) == 1

    def test_count_by_subject(self, service, mock_repo):
        mock_repo.count_by_subject.return_value = 5
        assert service.count_by_subject(uuid4()) == 5

    def test_update_processing_status(self, service, mock_repo):
        cid = uuid4()
        service.update_processing_status(cid, ContentSourceStatus.FAILED)
        mock_repo.update_status.assert_called_once_with(
            content_source_id=cid, status="failed"
        )

    def test_finish_ingestion(self, service, mock_repo):
        cid = uuid4()
        service.finish_ingestion(cid, "emb", 384, 100)
        mock_repo.finish_ingestion.assert_called_once_with(
            content_source_id=cid,
            embedding_model="emb",
            dimensions=384,
            chunks=100,
            total_tokens=None,
            max_tokens_per_chunk=None,
        )
