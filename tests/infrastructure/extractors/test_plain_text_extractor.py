from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.extractors.plain_text_extractor import PlainTextExtractor


class TestPlainTextExtractor:
    @pytest.fixture
    def extractor(self):
        return PlainTextExtractor()

    def test_extract_from_local_success(self, extractor, tmp_path):
        # Create a temporary text file
        test_file = tmp_path / "test.txt"
        content = "Hello, world!"
        test_file.write_text(content, encoding="utf-8")

        docs = extractor.extract(str(test_file))

        assert len(docs) == 1
        assert docs[0].page_content == content
        assert docs[0].metadata["file_name"] == "test.txt"
        assert docs[0].metadata["source_type"] == "txt"

    def test_extract_from_local_not_found(self, extractor):
        with pytest.raises(FileNotFoundError):
            extractor.extract("non_existent_file.txt")

    @patch("httpx.Client")
    def test_extract_from_url_success(self, mock_client_cls, extractor):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "URL content"
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response

        url = "https://example.com/file.py"
        docs = extractor.extract(url)

        assert len(docs) == 1
        assert docs[0].page_content == "URL content"
        assert docs[0].metadata["file_name"] == "file.py"
        assert docs[0].metadata["source_type"] == "py"
        mock_client.get.assert_called_once_with(url)

    @patch("httpx.Client")
    def test_extract_from_url_failure(self, mock_client_cls, extractor):
        mock_client = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = mock_client
        mock_client.get.side_effect = Exception("Connection error")

        url = "https://example.com/error.txt"
        with pytest.raises(ValueError, match="Failed to download content"):
            extractor.extract(url)
