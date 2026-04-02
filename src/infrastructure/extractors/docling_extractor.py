import os
import threading
from typing import List, Any

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from langchain_core.documents import Document

from src.config.logger import Logger
from src.config.settings import settings

logger = Logger()


class DoclingExtractor:
    """Extracts text and metadata from various file types using IBM's Docling with structural chunking."""

    _lock = threading.Lock()

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
        # By not specifying format_options, Docling enables all supported formats (PDF, DOCX, etc.)
        # However, we still want to pass our PDF pipeline options specifically.
        pdf_options = self._get_pipeline_options(do_ocr=False)
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
            }
        )
        # Lazy-loaded OCR converter
        self._ocr_converter = None

    def _get_ocr_converter(self) -> DocumentConverter:
        if self._ocr_converter is None:
            pdf_options = self._get_pipeline_options(do_ocr=True)
            self._ocr_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pdf_options),
                }
            )
        return self._ocr_converter

    def extract(self, file_path: str, do_ocr: bool = False) -> List[Document]:
        """
        Converts a file to a single LangChain Document containing the full Markdown content.
        """
        logger.info(
            "Starting extraction with Docling",
            context={"file_path": file_path, "do_ocr": do_ocr},
        )

        is_url = file_path.startswith(("http://", "https://"))
        if not is_url and not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            # 1. Convert
            result = self._convert_document(file_path, do_ocr)

            # 2. Metadata & Stats
            global_metadata = self._extract_metadata(result, file_path)
            
            # 3. Content
            raw_markdown = result.document.export_to_markdown()
            content = self._clean_text(raw_markdown)

            # 4. Build single document
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

    def _convert_document(self, file_path: str, do_ocr: bool) -> Any:
        with self._lock:
            converter = self._get_ocr_converter() if do_ocr else self.converter
            return converter.convert(file_path)

    def _extract_metadata(self, result: Any, file_path: str) -> dict:
        from docling_core.types.doc import PictureItem
        
        docling_source_type = "unknown"
        if hasattr(result, "input") and hasattr(result.input, "format"):
            docling_source_type = result.input.format.value

        image_count = 0
        for element, _level in result.document.iterate_items():
            if isinstance(element, PictureItem):
                image_count += 1

        origin_filename = self._get_origin_filename(result, file_path)
        extension = self._get_extension(origin_filename, file_path)

        metadata = {
            "source": file_path,
            "file_name": origin_filename,
            "source_type": extension,
            "docling_source_type": docling_source_type,
            "image_count": image_count,
            "is_structural_chunk": False,
            **self._get_document_stats(result.document)
        }

        # Doc-level metadata (title, authors, etc.)
        self._enrich_with_doc_meta(result, metadata)
        
        return metadata

    def _get_origin_filename(self, result: Any, file_path: str) -> str:
        origin_filename = os.path.basename(file_path)
        origin = getattr(result.document, "origin", None)
        if origin and getattr(origin, "filename", None):
            origin_filename = origin.filename
        return origin_filename

    def _get_extension(self, origin_filename: str, file_path: str) -> str:
        extension = os.path.splitext(origin_filename)[1].lower().lstrip(".")
        if not extension:
            extension = self._get_file_type(file_path)
        return extension

    def _get_document_stats(self, document: Any) -> dict:
        return {
            "num_pages": len(document.pages) if hasattr(document, "pages") else 0,
            "num_pictures": len(document.pictures) if hasattr(document, "pictures") else 0,
            "num_tables": len(document.tables) if hasattr(document, "tables") else 0,
            "num_groups": len(document.groups) if hasattr(document, "groups") else 0,
            "texts_count": len(document.texts) if hasattr(document, "texts") else 0,
            "key_value_items_count": len(document.key_value_items) if hasattr(document, "key_value_items") else 0,
            "form_items_count": len(document.form_items) if hasattr(document, "form_items") else 0,
            "field_items_count": len(document.field_items) if hasattr(document, "field_items") else 0,
        }

    def _enrich_with_doc_meta(self, result: Any, metadata: dict) -> None:
        doc_meta = None
        if hasattr(result.document, "meta"):
            doc_meta = result.document.meta
        elif (hasattr(result, "input") and hasattr(result.input, "document") and 
              hasattr(result.input.document, "meta")):
            doc_meta = result.input.document.meta

        if doc_meta:
            for attr in ["title", "authors", "description"]:
                if hasattr(doc_meta, attr) and getattr(doc_meta, attr):
                    metadata[attr] = getattr(doc_meta, attr)
            if hasattr(doc_meta, "date") and doc_meta.date:
                metadata["date"] = str(doc_meta.date)

    def _clean_text(self, text: str) -> str:
        """Fixes decomposed Portuguese characters common in PDF extractions."""
        import re
        import unicodedata

        # 1. NFC Normalization
        text = unicodedata.normalize("NFC", text)

        # 2. Regex for common decomposed patterns
        replacements = [
            (r"c\s*¸", "ç"), (r"¸\s*c", "ç"),
            (r"a\s*˜", "ã"), (r"˜\s*a", "ã"),
            (r"o\s*˜", "õ"), (r"˜\s*o", "õ"),
            (r"´\s*a", "á"), (r"a\s*´", "á"),
            (r"´\s*e", "é"), (r"e\s*´", "é"),
            (r"´\s*i", "í"), (r"i\s*´", "í"),
            (r"´\s*o", "ó"), (r"o\s*´", "ó"),
            (r"´\s*u", "ú"), (r"u\s*´", "ú"),
            (r"ˆ\s*a", "â"), (r"a\s*ˆ", "â"),
            (r"ˆ\s*e", "ê"), (r"e\s*ˆ", "ê"),
            (r"ˆ\s*o", "ô"), (r"o\s*ˆ", "ô"),
            (r"`\s*a", "à"), (r"a\s*`", "à"),
        ]

        for pattern, replacement in replacements:
            def fix_case(match, r=replacement):
                return r.upper() if match.group(0).isupper() else r.lower()

            text = re.sub(pattern, fix_case, text, flags=re.IGNORECASE)

        return text

    def _is_noisy_chunk(self, content: str) -> bool:
        """Heuristic to detect Table of Contents or Index noise."""
        dots_count = content.count(".")
        long_ellipses = content.count(" . . .")

        if len(content) < 1000 and (dots_count > 25 or long_ellipses > 5):
            return True

        import re
        toc_pattern = re.findall(r"\.\s*\.\s*\.\s*\d+\s*$", content, re.MULTILINE)
        return len(toc_pattern) > 3

    def _get_file_type(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower().lstrip(".")
        return ext or "unknown"
