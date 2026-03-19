import pytest
import uuid
from unittest.mock import MagicMock
from src.application.use_cases.knowledge_subject_use_case import KnowledgeSubjectUseCase
from src.domain.entities.knowledge_subject_entity import KnowledgeSubjectEntity
from src.domain.entities.content_source_entity import ContentSourceEntity
from datetime import datetime, timezone


@pytest.mark.KnowledgeSubjectUseCase
class TestKnowledgeSubjectUseCase:
    @pytest.fixture
    def mock_ks_service(self):
        return MagicMock()

    @pytest.fixture
    def mock_cs_use_case(self):
        return MagicMock()

    @pytest.fixture
    def mock_vector_repo(self):
        return MagicMock()

    @pytest.fixture
    def use_case(self, mock_ks_service, mock_cs_use_case, mock_vector_repo):
        return KnowledgeSubjectUseCase(
            ks_service=mock_ks_service,
            cs_use_case=mock_cs_use_case,
            vector_repo=mock_vector_repo,
        )

    def test_delete_knowledge_success(
        self, use_case, mock_ks_service, mock_cs_use_case, mock_vector_repo
    ):
        subject_id = uuid.uuid4()

        # 1. Subject exists
        mock_ks_service.get_subject_by_id.return_value = KnowledgeSubjectEntity(
            id=subject_id,
            name="Test Subject",
            created_at=datetime.now(timezone.utc),
            source_count=2,
        )

        # 2. Vector deletion succeeds
        mock_vector_repo.delete.return_value = 10

        # 3. Content sources found and deleted
        source1 = MagicMock(spec=ContentSourceEntity)
        source1.id = uuid.uuid4()
        source2 = MagicMock(spec=ContentSourceEntity)
        source2.id = uuid.uuid4()

        mock_cs_use_case.cs_service.list_by_subject.return_value = [source1, source2]
        mock_cs_use_case.delete.return_value = True

        # 4. Final subject deletion succeeds
        mock_ks_service.delete_subject.return_value = 1

        # Execute
        result = use_case.delete_knowledge(subject_id)

        # Assertions
        assert result is True
        mock_ks_service.get_subject_by_id.assert_called_once_with(subject_id)
        mock_vector_repo.delete.assert_called_once_with(
            filters={"subject_id": str(subject_id)}
        )
        mock_cs_use_case.cs_service.list_by_subject.assert_called_once_with(subject_id)
        assert mock_cs_use_case.delete.call_count == 2
        mock_ks_service.delete_subject.assert_called_once_with(subject_id)

    def test_delete_knowledge_not_found(
        self, use_case, mock_ks_service, mock_vector_repo
    ):
        subject_id = uuid.uuid4()
        mock_ks_service.get_subject_by_id.return_value = None

        result = use_case.delete_knowledge(subject_id)

        assert result is False
        mock_ks_service.get_subject_by_id.assert_called_once_with(subject_id)
        mock_vector_repo.delete.assert_not_called()

    def test_delete_knowledge_exception(
        self, use_case, mock_ks_service, mock_vector_repo
    ):
        subject_id = uuid.uuid4()
        mock_ks_service.get_subject_by_id.return_value = MagicMock()
        mock_vector_repo.delete.side_effect = Exception("Vector error")

        with pytest.raises(Exception, match="Vector error"):
            use_case.delete_knowledge(subject_id)
