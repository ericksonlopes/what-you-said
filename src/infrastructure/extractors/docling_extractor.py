import os
from typing import List

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from langchain_core.documents import Document

from src.config.logger import Logger
from src.config.settings import settings

logger = Logger()


class DoclingExtractor:
    """Extracts text and metadata from various file types using IBM's Docling with structural chunking."""

    def _get_pipeline_options(self, do_ocr: bool = False) -> PdfPipelineOptions:
        """Helper to create PdfPipelineOptions with consistent settings."""
        pipeline_options = PdfPipelineOptions()
        pipeline_options.accelerator_options.device = settings.app.device
        pipeline_options.do_ocr = do_ocr

        if settings.app.device == "cpu":
            pipeline_options.accelerator_options.num_threads = (
                settings.docling.cpu_num_threads
            )
        return pipeline_options

    def __init__(self):
        # Default converter (no OCR)
        pipeline_options = self._get_pipeline_options(do_ocr=False)
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        # Lazy-loaded OCR converter
        self._ocr_converter = None

    def _get_ocr_converter(self) -> DocumentConverter:
        if self._ocr_converter is None:
            pipeline_options = self._get_pipeline_options(do_ocr=True)
            self._ocr_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
        return self._ocr_converter

    def extract(self, file_path: str, do_ocr: bool = False) -> List[Document]:
        """
        Converts a file to a single LangChain Document containing the full Markdown content.

        Args:
            file_path: Path to the local file.
            do_ocr: Whether to use OCR for extraction.

        Returns:
            A list containing a single Document object.
        """
        logger.info(
            "Starting extraction with Docling",
            context={
                "file_path": file_path,
                "do_ocr": do_ocr,
            },
        )

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            # 1. Convert the document using the appropriate converter
            converter = self._get_ocr_converter() if do_ocr else self.converter
            result = converter.convert(file_path)

            # 2. Extract global metadata
            from docling_core.types.doc import PictureItem

            doc_meta = None
            if hasattr(result.document, "meta"):
                doc_meta = result.document.meta
            elif (
                hasattr(result, "input")
                and hasattr(result.input, "document")
                and hasattr(result.input.document, "meta")
            ):
                doc_meta = result.input.document.meta

            # Get Docling-detected source type and count images
            docling_source_type = "unknown"
            if hasattr(result, "input") and hasattr(result.input, "format"):
                docling_source_type = result.input.format.value

            image_count = 0
            for element, _level in result.document.iterate_items():
                if isinstance(element, PictureItem):
                    image_count += 1

            # Get original filename and extension
            origin_filename = os.path.basename(file_path)
            origin = getattr(result.document, "origin", None)
            if origin and getattr(origin, "filename", None):
                origin_filename = origin.filename

            # Extension from origin_filename
            extension = os.path.splitext(origin_filename)[1].lower().lstrip(".")
            if not extension:
                extension = self._get_file_type(file_path)

            logger.debug(
                "Extracted metadata from Docling",
                context={
                    "origin_filename": origin_filename,
                    "extension": extension,
                    "docling_source_type": docling_source_type,
                    "image_count": image_count,
                },
            )

            global_metadata = {
                "source": file_path,
                "file_name": origin_filename,
                "file_type": extension,
                "source_type": extension,
                "docling_source_type": docling_source_type,
                "image_count": image_count,
                "is_structural_chunk": False,  # No longer pre-chunked
            }

            if doc_meta:
                for attr in ["title", "authors", "description"]:
                    if hasattr(doc_meta, attr) and getattr(doc_meta, attr):
                        global_metadata[attr] = getattr(doc_meta, attr)
                if hasattr(doc_meta, "date") and doc_meta.date:
                    global_metadata["date"] = str(doc_meta.date)

            # 3. Export to Markdown
            # Docling's result.document can be exported to markdown
            raw_markdown = result.document.export_to_markdown()

            # 4. Clean text
            content = self._clean_text(raw_markdown)

            # 5. Build single document
            doc = Document(page_content=content, metadata=global_metadata)

            logger.info(
                "Successfully extracted full Markdown with Docling",
                context={"file_path": file_path, "content_length": len(content)},
            )
            return [doc]

        except Exception as e:
            logger.error(
                f"Error extracting with Docling: {e}", context={"file_path": file_path}
            )
            raise ValueError(f"Failed to extract content from {file_path}: {str(e)}")

    def _clean_text(self, text: str) -> str:
        """Fixes decomposed Portuguese characters common in PDF extractions."""
        import re
        import unicodedata

        # 1. NFC Normalization (combines characters if they are standard Unicode sequences)
        text = unicodedata.normalize("NFC", text)

        # 2. Regex for common decomposed patterns in "broken" PDFs
        # Decomposed patterns can have diacritics BEFORE or AFTER the character
        replacements = [
            (r"c\s*¸", "ç"),
            (r"¸\s*c", "ç"),
            (r"a\s*˜", "ã"),
            (r"˜\s*a", "ã"),
            (r"o\s*˜", "õ"),
            (r"˜\s*o", "õ"),
            (r"´\s*a", "á"),
            (r"a\s*´", "á"),
            (r"´\s*e", "é"),
            (r"e\s*´", "é"),
            (r"´\s*i", "í"),
            (r"i\s*´", "í"),
            (r"´\s*o", "ó"),
            (r"o\s*´", "ó"),
            (r"´\s*u", "ú"),
            (r"u\s*´", "ú"),
            (r"ˆ\s*a", "â"),
            (r"a\s*ˆ", "â"),
            (r"ˆ\s*e", "ê"),
            (r"e\s*ˆ", "ê"),
            (r"ˆ\s*o", "ô"),
            (r"o\s*ˆ", "ô"),
            (r"`\s*a", "à"),
            (r"a\s*`", "à"),
        ]

        for pattern, replacement in replacements:
            # We use a custom sub to handle case preservation for simple cases
            def fix_case(match):
                if match.group(0).isupper():
                    return replacement.upper()
                return replacement.lower()

            text = re.sub(pattern, fix_case, text, flags=re.IGNORECASE)

        return text

    def _is_noisy_chunk(self, content: str) -> bool:
        """Heuristic to detect Table of Contents or Index noise."""
        # TOCs usually have lots of dots (........) or numbers separated by dots
        dots_count = content.count(".")
        long_ellipses = content.count(" . . .")

        # If the content is small and has many dots, it's likely a TOC fragment
        if len(content) < 1000 and (dots_count > 25 or long_ellipses > 5):
            return True

        # Check for numeric-only lines or lines with very few words and a page number at the end
        import re

        toc_pattern = re.findall(r"\.\s*\.\s*\.\s*\d+\s*$", content, re.MULTILINE)
        if len(toc_pattern) > 3:
            return True

        return False

    def _get_file_type(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower().lstrip(".")
        return ext or "unknown"
