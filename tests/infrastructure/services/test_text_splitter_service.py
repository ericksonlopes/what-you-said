from unittest.mock import MagicMock

import pytest

from src.infrastructure.services.text_splitter_service import TextSplitterService


class TestTextSplitterService:
    @pytest.fixture
    def mock_tokenizer(self):
        tokenizer = MagicMock()
        # Mock encode: returns a list of integer IDs
        # For simple testing, each word is an ID
        tokenizer.encode.side_effect = lambda text, **kwargs: [ord(c) for c in text]
        # Mock decode: converts IDs back to characters
        tokenizer.decode.side_effect = lambda ids, **kwargs: "".join(
            chr(i) for i in ids
        )
        return tokenizer

    def test_split_text_success(self, mock_tokenizer):
        service = TextSplitterService(tokenizer=mock_tokenizer)
        text = "Hello World!"  # 12 characters -> 12 tokens
        tokens_per_chunk = 5
        tokens_overlap = 2

        # Step = 5 - 2 = 3
        # Chunk 1: tokens[0:5] = "Hello" (5 tokens)
        # Chunk 2: tokens[3:8] = "lo Wo" (5 tokens)
        # Chunk 3: tokens[6:11] = " Worl" (5 tokens)
        # Chunk 4: tokens[9:12] = "ld!" (3 tokens)

        docs = service.split_text(
            text=text,
            tokens_per_chunk=tokens_per_chunk,
            tokens_overlap=tokens_overlap,
            metadata={"source": "test"},
        )

        assert len(docs) == 4
        assert docs[0].page_content == "Hello"
        assert docs[0].metadata["token_count"] == 5
        assert docs[0].metadata["chunk_index"] == 0
        assert docs[0].metadata["source"] == "test"

        assert docs[1].page_content == "lo Wo"
        assert docs[1].metadata["token_count"] == 5
        assert docs[1].metadata["chunk_index"] == 1

        assert docs[2].page_content == "World"
        assert docs[3].page_content == "ld!"
        assert docs[3].metadata["token_count"] == 3

    def test_split_text_empty(self, mock_tokenizer):
        service = TextSplitterService(tokenizer=mock_tokenizer)
        docs = service.split_text(text="")
        assert len(docs) == 0

    def test_split_text_invalid_params(self, mock_tokenizer):
        service = TextSplitterService(tokenizer=mock_tokenizer)
        with pytest.raises(ValueError) as excinfo:
            service.split_text(text="some text", tokens_per_chunk=10, tokens_overlap=10)
        assert "tokens_per_chunk must be greater than tokens_overlap" in str(
            excinfo.value
        )

    def test_split_text_tokenizer_type_error(self, mock_tokenizer):
        # Test the fallback in split_text if add_special_tokens=False is not supported
        mock_tokenizer.encode.side_effect = [
            TypeError("No add_special_tokens"),
            [ord(c) for c in "test"],
        ]
        service = TextSplitterService(tokenizer=mock_tokenizer)
        docs = service.split_text(text="test")
        assert len(docs) == 1
        assert docs[0].page_content == "test"

    def test_split_text_tokenizer_general_exception(self, mock_tokenizer):
        # Test line 58-59: general exception fallback to len(text) // 4
        mock_tokenizer.encode.side_effect = Exception("Fatal")
        service = TextSplitterService(tokenizer=mock_tokenizer)
        docs = service.split_text(text="test text")
        assert len(docs) == 1
        # len("test text") is 9. 9 // 4 = 2 tokens estimated.
        assert docs[0].metadata["token_count"] == 2
