import os
from typing import List
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from langchain_core.documents import Document

from src.config.logger import Logger

logger = Logger()


class DoclingExtractor:
    """Extracts text and metadata from various file types using IBM's Docling with structural chunking."""

    def __init__(self):
        # Default converter for use in Linux/High-resource environments
        self.converter = DocumentConverter()
        # Default chunker for structural splitting
        self.chunker = HybridChunker()

    def extract(self, file_path: str) -> List[Document]:
        """
        Converts a file to a list of chunked LangChain Documents.

        Args:
            file_path: Path to the local file.

        Returns:
            A list of Document objects, each representing a structural chunk.
        """
        logger.info(
            "Starting structural extraction with Docling",
            context={"file_path": file_path},
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
                "is_structural_chunk": True,  # Tag for the use case to know it's already chunked
            }

            if doc_meta:
                for attr in ["title", "authors", "description"]:
                    if hasattr(doc_meta, attr) and getattr(doc_meta, attr):
                        global_metadata[attr] = getattr(doc_meta, attr)
                if hasattr(doc_meta, "date") and doc_meta.date:
                    global_metadata["date"] = str(doc_meta.date)

            # 3. Perform structural chunking
            chunks = list(self.chunker.chunk(result.document))

            extracted_docs = []
            for i, chunk in enumerate(chunks):
                # Serialize chunk to markdown/text
                raw_content = self.chunker.serialize(chunk)

                # 4. Clean and Filter content
                if self._is_noisy_chunk(raw_content):
                    logger.debug(
                        f"Skipping noisy chunk {i} (likely TOC or Index)",
                        context={"chunk_index": i},
                    )
                    continue

                content = self._clean_text(raw_content)

                # Chunk-specific metadata
                chunk_metadata = global_metadata.copy()
                chunk_metadata["chunk_index"] = i

                # Extract page numbers from chunk provenance
                pages = set()
                if hasattr(chunk, "meta") and hasattr(chunk.meta, "doc_items"):
                    for item in chunk.meta.doc_items:
                        if hasattr(item, "prov") and item.prov:
                            for p in item.prov:
                                if hasattr(p, "page_no"):
                                    pages.add(p.page_no)

                if pages:
                    sorted_pages = sorted(list(pages))
                    chunk_metadata["pages"] = sorted_pages
                    chunk_metadata["page_label"] = ", ".join(map(str, sorted_pages))

                # Extract headings (document hierarchy)
                if (
                    hasattr(chunk, "meta")
                    and hasattr(chunk.meta, "headings")
                    and chunk.meta.headings
                ):
                    chunk_metadata["headings"] = chunk.meta.headings
                    chunk_metadata["current_section"] = (
                        chunk.meta.headings[-1] if chunk.meta.headings else None
                    )

                extracted_docs.append(
                    Document(page_content=content, metadata=chunk_metadata)
                )

            logger.info(
                "Successfully extracted structural chunks with Docling",
                context={"file_path": file_path, "chunks_count": len(extracted_docs)},
            )
            return extracted_docs

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
