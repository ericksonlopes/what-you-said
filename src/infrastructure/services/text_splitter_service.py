from typing import Any, Dict, List, Optional
from langchain_core.documents import Document
from src.config.logger import Logger

logger = Logger()


class TextSplitterService:
    """Generic service for splitting text into token-based chunks."""

    def __init__(self, tokenizer: Any):
        self.tokenizer = tokenizer

    def split_text(
        self,
        text: str,
        tokens_per_chunk: int = 512,
        tokens_overlap: int = 50,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Document]:
        """
        Splits text into chunks of specified token size with overlap.

        Args:
            text: The full text to split (usually Markdown).
            tokens_per_chunk: Maximum tokens per chunk.
            tokens_overlap: Overlap between chunks in tokens.
            metadata: Base metadata to include in each chunk.

        Returns:
            A list of Document objects.
        """
        if not text:
            return []

        if tokens_per_chunk <= tokens_overlap:
            raise ValueError("tokens_per_chunk must be greater than tokens_overlap")

        step = tokens_per_chunk - tokens_overlap

        # 1. Tokenize the full text
        documents: List[Document] = []
        n = 0
        try:
            try:
                token_ids = self.tokenizer.encode(text, add_special_tokens=False)
            except TypeError:
                token_ids = self.tokenizer.encode(text)

            n = len(token_ids)

            i = 0
            chunk_index = 0
            while i < n:
                chunk_ids = token_ids[i : i + tokens_per_chunk]

                # 2. Decode back to text
                try:
                    chunk_text = self.tokenizer.decode(
                        chunk_ids, skip_special_tokens=True
                    )
                except Exception:
                    chunk_text = self.tokenizer.decode(chunk_ids)

                chunk_metadata = (metadata or {}).copy()
                chunk_metadata.update(
                    {"token_count": len(chunk_ids), "chunk_index": chunk_index}
                )

                documents.append(
                    Document(page_content=chunk_text, metadata=chunk_metadata)
                )

                i += step
                chunk_index += 1
        except Exception as e:
            logger.error(
                e,
                context={
                    "action": "split_text",
                    "text_length": len(text),
                    "message": "Falling back to character-based split",
                },
            )
            # Use a basic character-based split as fallback to avoid "all-in-one-chunk" monster chunks
            from langchain_text_splitters import RecursiveCharacterTextSplitter

            # 1 token approx 4 chars. 512 tokens -> 2048 chars
            char_splitter = RecursiveCharacterTextSplitter(
                chunk_size=tokens_per_chunk * 4, chunk_overlap=tokens_overlap * 4
            )
            backup_docs = char_splitter.split_text(text)

            for idx, content in enumerate(backup_docs):
                chunk_metadata = (metadata or {}).copy()
                chunk_metadata.update(
                    {
                        "token_count": len(content) // 4,
                        "chunk_index": idx,
                        "is_fallback": True,
                    }
                )
                documents.append(
                    Document(page_content=content, metadata=chunk_metadata)
                )

        return documents
