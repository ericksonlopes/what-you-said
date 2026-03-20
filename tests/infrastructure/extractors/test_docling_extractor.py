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
        mock_result.document.origin.filename = None  # Force fallback
        mock_converter.convert.return_value = mock_result

        # Mock input format
        mock_result.input.format.value = "docx"

        # Mock result.document.export_to_markdown
        mock_result.document.export_to_markdown.return_value = "# Markdown Content"

        # Mock result.document.iterate_items for image counting
        mock_result.document.iterate_items.return_value = []

        extractor = DoclingExtractor()
        docs = extractor.extract(str(test_file))

        assert len(docs) == 1
        assert docs[0].page_content == "# Markdown Content"
        assert docs[0].metadata["file_name"] == "test.docx"
        assert docs[0].metadata["is_structural_chunk"] is False
        assert docs[0].metadata["source"] == str(test_file)
        assert docs[0].metadata["docling_source_type"] == "docx"
        assert docs[0].metadata["image_count"] == 0

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

    def test_extract_with_metadata(self, mock_converter, tmp_path):
        from src.infrastructure.extractors.docling_extractor import DoclingExtractor

        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        mock_result = MagicMock()
        mock_result.document.origin.filename = None  # Force fallback
        mock_result.document.export_to_markdown.return_value = "content"
        # Mock metadata
        mock_result.document.meta.title = "Test Title"
        mock_result.document.meta.authors = ["Author 1"]
        mock_result.document.meta.date = "2024-01-01"

        mock_converter.convert.return_value = mock_result

        extractor = DoclingExtractor()
        docs = extractor.extract(str(test_file))

        assert len(docs) == 1
        assert docs[0].page_content == "content"
        assert docs[0].metadata["title"] == "Test Title"
        assert docs[0].metadata["authors"] == ["Author 1"]
        assert docs[0].metadata["date"] == "2024-01-01"
        assert docs[0].metadata["file_name"] == "test.pdf"

    def test_clean_text_portuguese_chars(self):
        from src.infrastructure.extractors.docling_extractor import DoclingExtractor

        extractor = DoclingExtractor()
        # Test decomposed characters
        # "c  ¸" -> "ç"
        # "a  ˜" -> "ã"
        # "´  e" -> "é"
        text = "Conceic ¸ao, ac ˜ao, cafe ´"
        cleaned = extractor._clean_text(text)
        assert "Conceiçao" in cleaned
        assert "ac ão" in cleaned
        assert "café" in cleaned

        # Uppercase
        text_up = "CONCEIC ¸AO"
        cleaned_up = extractor._clean_text(text_up)
        assert "CONCEIÇAO" in cleaned_up

    def test_is_noisy_chunk(self):
        from src.infrastructure.extractors.docling_extractor import DoclingExtractor

        extractor = DoclingExtractor()
        # TOC like content
        toc_content = (
            "Chapter 1 . . . . . . . . . . . 1\nChapter 2 . . . . . . . . . . . 2"
        )
        assert extractor._is_noisy_chunk(toc_content) is True

        normal_content = "This is a normal paragraph of text with no noise."
        assert extractor._is_noisy_chunk(normal_content) is False

    def test_get_file_type(self):
        from src.infrastructure.extractors.docling_extractor import DoclingExtractor

        extractor = DoclingExtractor()
        assert extractor._get_file_type("test.PDF") == "pdf"
        assert extractor._get_file_type("no_ext") == "unknown"

    def test_extract_with_images(self, mock_converter, tmp_path):
        from src.infrastructure.extractors.docling_extractor import DoclingExtractor
        from docling_core.types.doc import PictureItem

        test_file = tmp_path / "images.pdf"
        test_file.write_text("dummy")

        mock_result = MagicMock()
        mock_result.input.format.value = "pdf"
        mock_result.document.export_to_markdown.return_value = "content"

        # Mock 2 images
        image1 = MagicMock(spec=PictureItem)
        image2 = MagicMock(spec=PictureItem)
        other_item = MagicMock()

        mock_result.document.iterate_items.return_value = [
            (image1, 0),
            (other_item, 0),
            (image2, 1),
        ]

        mock_converter.convert.return_value = mock_result

        extractor = DoclingExtractor()
        docs = extractor.extract(str(test_file))

        assert len(docs) == 1
        assert docs[0].metadata["image_count"] == 2
        assert docs[0].metadata["docling_source_type"] == "pdf"
