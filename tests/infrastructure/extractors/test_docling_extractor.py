import pytest
from unittest.mock import MagicMock


@pytest.mark.DoclingExtractor
class TestDoclingExtractor:
    @pytest.fixture
    def mock_converter(self, monkeypatch):
        mock = MagicMock()
        # Mocking the class in the module where it is used
        monkeypatch.setattr(
            "src.infrastructure.extractors.docling_extractor.DocumentConverter",
            lambda *args, **kwargs: mock,
        )
        return mock

    def test_extract_success(self, mock_converter, tmp_path):
        from src.infrastructure.extractors.docling_extractor import DoclingExtractor

        # Setup mock converter
        test_file = tmp_path / "test.docx"
        test_file.write_text("dummy")

        mock_result = MagicMock()
        mock_converter.convert.return_value = mock_result

        # Mock result.document.export_to_markdown
        mock_result.document.export_to_markdown.return_value = "# Markdown Content"

        extractor = DoclingExtractor()
        docs = extractor.extract(str(test_file))

        assert len(docs) == 1
        assert docs[0].page_content == "# Markdown Content"
        assert docs[0].metadata["file_name"] == "test.docx"
        assert docs[0].metadata["is_structural_chunk"] is False
        assert docs[0].metadata["source"] == str(test_file)

    def test_extract_file_not_found(self):
        from src.infrastructure.extractors.docling_extractor import DoclingExtractor

        extractor = DoclingExtractor()
        with pytest.raises(FileNotFoundError):
            extractor.extract("non_existent_file.pdf")

    def test_extract_failure(self, mock_converter, tmp_path):
        from src.infrastructure.extractors.docling_extractor import DoclingExtractor

        test_file = tmp_path / "fail.pdf"
        test_file.write_text("dummy")

        mock_converter.convert.side_effect = Exception("Docling error")

        extractor = DoclingExtractor()
        with pytest.raises(ValueError) as excinfo:
            extractor.extract(str(test_file))
        assert "Failed to extract content" in str(excinfo.value)
