import os
from typing import List

import httpx
from langchain_core.documents import Document

from src.config.logger import Logger

logger = Logger()


class PlainTextExtractor:
    """Extracts text from plain text and source code files (txt, py, js, etc.)."""

    def __init__(self):
        self.timeout = 30.0
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def extract(self, file_path_or_url: str) -> List[Document]:
        """
        Extracts content from a local file or URL.

        Args:
            file_path_or_url: Path to the local file or a URL.

        Returns:
            A list containing a single Document object.
        """
        is_url = file_path_or_url.startswith(("http://", "https://"))

        if is_url:
            return self._extract_from_url(file_path_or_url)
        else:
            return self._extract_from_local(file_path_or_url)

    def _extract_from_url(self, url: str) -> List[Document]:
        logger.info("Extracting plain text from URL", context={"url": url})
        try:
            with httpx.Client(
                follow_redirects=True, headers=self.headers, timeout=self.timeout
            ) as client:
                response = client.get(url)
                response.raise_for_status()
                content = response.text

                filename = url.split("/")[-1].split("?")[0] or "downloaded_file"
                extension = os.path.splitext(filename)[1].lower().lstrip(".") or "txt"

                metadata = self._build_metadata(url, filename, extension)

                return [Document(page_content=content, metadata=metadata)]
        except Exception as e:
            logger.error(
                "Error downloading plain text from URL",
                context={"url": url, "error": str(e)},
            )
            raise ValueError(f"Failed to download content from {url}: {str(e)}")

    def _extract_from_local(self, file_path: str) -> List[Document]:
        logger.info(
            "Extracting plain text from local file", context={"file_path": file_path}
        )
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            filename = os.path.basename(file_path)
            extension = os.path.splitext(filename)[1].lower().lstrip(".") or "txt"

            metadata = self._build_metadata(file_path, filename, extension)

            return [Document(page_content=content, metadata=metadata)]
        except Exception as e:
            logger.error(
                "Error reading local plain text file",
                context={"file_path": file_path, "error": str(e)},
            )
            raise ValueError(f"Failed to read content from {file_path}: {str(e)}")

    @staticmethod
    def _build_metadata(source: str, filename: str, extension: str) -> dict:
        return {
            "source": source,
            "file_name": filename,
            "source_type": extension,
            "docling_source_type": "plain_text",
            "is_structural_chunk": False,
        }
