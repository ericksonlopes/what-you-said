import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from types import SimpleNamespace
from datetime import datetime, timezone
from src.infrastructure.services.knowledge_subject_service import (
    KnowledgeSubjectService,
)


@pytest.mark.KnowledgeSubjectService
class TestKnowledgeSubjectService:
    @pytest.fixture
    def mock_repo(self):
        return MagicMock()

    @pytest.fixture
    def service(self, mock_repo):
        return KnowledgeSubjectService(repository=mock_repo)

    def create_mock_model(self, **kwargs):
        defaults = {
            "id": uuid4(),
            "name": "Test Subject",
            "external_ref": "ref1",
            "description": "desc",
            "icon": "icon",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    def test_create_subject(self, service, mock_repo):
        sid = uuid4()
        mock_repo.create_subject.return_value = sid
        mock_repo.get_by_id.return_value = self.create_mock_model(id=sid, name="New")

        result = service.create_subject(
            name="New", external_ref="ref", description="d", icon="i"
        )

        assert result.id == sid
        assert result.name == "New"
        mock_repo.create_subject.assert_called_once_with(
            name="New", external_ref="ref", description="d", icon="i"
        )

    def test_get_by_name(self, service, mock_repo):
        mock_repo.get_by_name.return_value = self.create_mock_model(name="Target")
        result = service.get_by_name("Target")
        assert result.name == "Target"
        mock_repo.get_by_name.assert_called_once_with("Target")

    def test_get_subject_by_id(self, service, mock_repo):
        sid = uuid4()
        mock_repo.get_by_id.return_value = self.create_mock_model(id=sid)
        result = service.get_subject_by_id(sid)
        assert result.id == sid
        mock_repo.get_by_id.assert_called_once_with(sid)

    def test_get_subject_by_external_ref(self, service, mock_repo):
        mock_repo.get_by_external_ref.return_value = self.create_mock_model(
            external_ref="ref123"
        )
        result = service.get_subject_by_external_ref("ref123")
        assert result.external_ref == "ref123"
        mock_repo.get_by_external_ref.assert_called_once_with("ref123")

    def test_get_or_create_by_external_ref_existing(self, service, mock_repo):
        mock_repo.get_by_external_ref.return_value = self.create_mock_model(
            external_ref="ext"
        )
        result = service.get_or_create_by_external_ref("ext")
        assert result.external_ref == "ext"
        mock_repo.create_subject.assert_not_called()

    def test_get_or_create_by_external_ref_new(self, service, mock_repo):
        mock_repo.get_by_external_ref.side_effect = [
            None,
            self.create_mock_model(external_ref="ext", name="Name"),
        ]
        mock_repo.create_subject.return_value = uuid4()
        mock_repo.get_by_id.return_value = self.create_mock_model(
            external_ref="ext", name="Name"
        )

        result = service.get_or_create_by_external_ref("ext", name="Name")

        assert result.external_ref == "ext"
        assert result.name == "Name"
        mock_repo.create_subject.assert_called_once()

    def test_list_subjects(self, service, mock_repo):
        mock_repo.list.return_value = [
            self.create_mock_model(),
            self.create_mock_model(),
        ]
        result = service.list_subjects(limit=10)
        assert len(result) == 2
        mock_repo.list.assert_called_once_with(10)

    def test_update_subject(self, service, mock_repo):
        sid = uuid4()
        service.update_subject(sid, name="Updated")
        mock_repo.update.assert_called_once_with(
            id=sid, name="Updated", description=None, external_ref=None, icon=None
        )

    def test_delete_subject(self, service, mock_repo):
        sid = uuid4()
        mock_repo.delete.return_value = 1
        result = service.delete_subject(sid)
        assert result == 1
        mock_repo.delete.assert_called_once_with(sid)
