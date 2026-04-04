import pytest
from unittest.mock import MagicMock, patch
from src.infrastructure.repositories.storage.storage import StorageService


@pytest.mark.StorageService
class TestStorageService:
    @patch("boto3.client")
    def test_ensure_bucket_creates_if_missing(self, mock_boto):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3

        # Simulate bucket not found
        mock_s3.head_bucket.side_effect = Exception("Not Found")

        svc = StorageService()

        assert mock_s3.create_bucket.called
        assert svc.bucket == "whatyousaid"

    @patch("boto3.client")
    def test_upload_file(self, mock_boto):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        svc = StorageService()

        result = svc.upload_file("local.wav", "remote.wav")

        assert result == "remote.wav"
        mock_s3.upload_file.assert_called_with("local.wav", svc.bucket, "remote.wav")

    @patch("boto3.client")
    def test_download_file(self, mock_boto):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        svc = StorageService()

        with patch("os.makedirs"):
            result = svc.download_file("remote.wav", "local.wav")

        assert result == "local.wav"
        mock_s3.download_file.assert_called_with(svc.bucket, "remote.wav", "local.wav")

    @patch("boto3.client")
    def test_list_files(self, mock_boto):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        svc = StorageService()

        # Mock paginator
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        import datetime

        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {
                        "Key": "file1.wav",
                        "Size": 100,
                        "LastModified": datetime.datetime(2023, 1, 1),
                    },
                    {
                        "Key": "file2.txt",
                        "Size": 200,
                        "LastModified": datetime.datetime(2023, 1, 1),
                    },
                ]
            }
        ]

        # Test without extension filter
        files = svc.list_files(prefix="test/")
        assert len(files) == 2

        # Test with extension filter
        files_wav = svc.list_files(prefix="test/", extension=".wav")
        assert len(files_wav) == 1
        assert files_wav[0]["key"] == "file1.wav"

    @patch("boto3.client")
    def test_get_presigned_url(self, mock_boto):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        svc = StorageService()

        mock_s3.generate_presigned_url.return_value = "http://signed-url"

        url = svc.get_presigned_url("remote.wav")
        assert url == "http://signed-url"
        mock_s3.generate_presigned_url.assert_called_with(
            "get_object",
            Params={"Bucket": svc.bucket, "Key": "remote.wav"},
            ExpiresIn=3600,
        )

    @patch("boto3.client")
    def test_delete_file(self, mock_boto):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        svc = StorageService()

        svc.delete_file("remote.wav")
        mock_s3.delete_object.assert_called_with(Bucket=svc.bucket, Key="remote.wav")

    @patch("boto3.client")
    def test_list_files_empty(self, mock_boto):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        svc = StorageService()

        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{}]  # Empty page

        files = svc.list_files(prefix="test/")
        assert len(files) == 0

    @patch("boto3.client")
    @patch("src.infrastructure.repositories.storage.storage.logger")
    def test_ensure_bucket_already_exists(self, mock_logger, mock_boto):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        mock_s3.head_bucket.return_value = {}  # Exists

        StorageService()

        assert not mock_s3.create_bucket.called

    @patch("boto3.client")
    def test_upload_file_path_resolution(self, mock_boto):
        mock_s3 = MagicMock()
        mock_boto.return_value = mock_s3
        svc = StorageService()

        # Test default destination
        svc.upload_file("local.wav")
        mock_s3.upload_file.assert_called_with("local.wav", svc.bucket, "local.wav")
