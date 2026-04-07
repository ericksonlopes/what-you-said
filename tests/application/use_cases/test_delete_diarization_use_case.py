import pytest
from unittest.mock import patch

from src.application.use_cases.delete_diarization_use_case import (
    DeleteDiarizationUseCase,
)
from src.infrastructure.repositories.sql.models.diarization_record import (
    DiarizationRecord,
)


@pytest.mark.usefixtures("sqlite_memory")
class TestDeleteDiarizationUseCase:
    @pytest.fixture
    def mock_storage(self):
        with patch(
            "src.application.use_cases.delete_diarization_use_case.StorageService"
        ) as mock:
            instance = mock.return_value
            instance.bucket = "test-bucket"
            yield instance

    @pytest.fixture
    def mock_cs_service(self):
        return patch("src.infrastructure.services.content_source_service.ContentSourceService").start()

    def test_execute_success(self, sqlite_memory, mock_storage, mock_cs_service):
        # Setup record
        record = DiarizationRecord(
            id="test-id",
            name="Test",
            storage_path="s3://test-bucket/prefix/",
            folder_path="/tmp/local/folder",
            segments=[],
        )
        sqlite_memory.add(record)
        sqlite_memory.commit()

        use_case = DeleteDiarizationUseCase(sqlite_memory, cs_service=mock_cs_service, storage_service=mock_storage)

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.isdir", return_value=True),
            patch("shutil.rmtree") as mock_rmtree,
        ):
            result = use_case.execute("test-id")

            assert result is True
            mock_storage.delete_directory.assert_called_once_with("prefix/")
            mock_rmtree.assert_called_once_with("/tmp/local/folder")

            # Verify DB deletion
            deleted_record = (
                sqlite_memory.query(DiarizationRecord).filter_by(id="test-id").first()
            )
            assert deleted_record is None

    def test_execute_not_found(self, sqlite_memory, mock_storage, mock_cs_service):
        use_case = DeleteDiarizationUseCase(sqlite_memory, cs_service=mock_cs_service, storage_service=mock_storage)
        result = use_case.execute("non-existent")
        assert result is False

    def test_execute_no_paths(self, sqlite_memory, mock_storage, mock_cs_service):
        record = DiarizationRecord(
            id="test-id-no-paths",
            name="Test",
            storage_path=None,
            folder_path=None,
            segments=[],
        )
        sqlite_memory.add(record)
        sqlite_memory.commit()

        use_case = DeleteDiarizationUseCase(sqlite_memory, cs_service=mock_cs_service, storage_service=mock_storage)
        result = use_case.execute("test-id-no-paths")

        assert result is True
        mock_storage.delete_directory.assert_not_called()

        deleted_record = (
            sqlite_memory.query(DiarizationRecord)
            .filter_by(id="test-id-no-paths")
            .first()
        )
        assert deleted_record is None

    def test_execute_s3_error_continues(self, sqlite_memory, mock_storage, mock_cs_service):
        record = DiarizationRecord(
            id="test-id-s3-error",
            name="Test",
            storage_path="s3://test-bucket/prefix/",
            segments=[],
        )
        sqlite_memory.add(record)
        sqlite_memory.commit()

        mock_storage.delete_directory.side_effect = Exception("S3 Delete Failed")

        use_case = DeleteDiarizationUseCase(sqlite_memory, cs_service=mock_cs_service, storage_service=mock_storage)
        result = use_case.execute("test-id-s3-error")

        # Should still return true because DB deletion succeeds
        assert result is True
        mock_storage.delete_directory.assert_called_once()

        deleted_record = (
            sqlite_memory.query(DiarizationRecord)
            .filter_by(id="test-id-s3-error")
            .first()
        )
        assert deleted_record is None

    def test_execute_local_file_instead_of_dir(self, sqlite_memory, mock_storage, mock_cs_service):
        record = DiarizationRecord(
            id="test-id-file",
            name="Test",
            folder_path="/tmp/local/file.txt",
            segments=[],
        )
        sqlite_memory.add(record)
        sqlite_memory.commit()

        use_case = DeleteDiarizationUseCase(sqlite_memory, cs_service=mock_cs_service, storage_service=mock_storage)

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.isdir", return_value=False),
            patch("os.remove") as mock_remove,
        ):
            result = use_case.execute("test-id-file")

            assert result is True
            mock_remove.assert_called_once_with("/tmp/local/file.txt")

            deleted_record = (
                sqlite_memory.query(DiarizationRecord)
                .filter_by(id="test-id-file")
                .first()
            )
            assert deleted_record is None
