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

    def __init__(self):
        # Configure pipeline options with the device from settings (CUDA or CPU)
        pipeline_options = PdfPipelineOptions()
        pipeline_options.accelerator_options.device = settings.app.device

        # Optimization for low memory / CPU environments
        # Default to 1 thread to avoid peak memory usage causing std::bad_alloc
        if settings.app.device == "cpu":
            pipeline_options.accelerator_options.num_threads = (
                settings.docling.cpu_num_threads
            )

        # Default converter for use in Linux/High-resource environments
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def extract(self, file_path: str) -> List[Document]:
        """
        Converts a file to a single LangChain Document containing the full Markdown content.

        Args:
            file_path: Path to the local file.

        Returns:
            A list containing a single Document object.
        """
        logger.info(
            "Starting extraction with Docling",
            context={
                "file_path": file_path,
            },
        )

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            # 1. Convert the document
            result = self.converter.convert(file_path)

            # 2. Extract global metadata
            doc_meta = None
            if hasattr(result.document, "meta"):
                doc_meta = result.document.meta
            elif (
                hasattr(result, "input")
                and hasattr(result.input, "document")
                and hasattr(result.input.document, "meta")
            ):
                doc_meta = result.input.document.meta

            global_metadata = {
                "source": file_path,
                "file_name": os.path.basename(file_path),
                "file_type": self._get_file_type(file_path),
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
            # Handle lowercase
            text = re.sub(pattern, replacement, text)
            # Handle uppercase
            text = re.sub(pattern.upper(), replacement.upper(), text)

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
