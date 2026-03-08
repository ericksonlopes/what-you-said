from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from src.infrastructure.services.youtube_text_temporal_splitter_service import YoutubeTranscriptSplitterService
from src.infrastructure.services.youtube_text_temporal_splitter_service import logger


class DummySnippet:
    def __init__(self, text, start, duration):
        self.text = text
        self.start = start
        self.duration = duration


class DummyTranscript(list):
    video_id = "dummy_video_id"


@pytest.fixture
def dummy_transcript():
    return DummyTranscript([
        DummySnippet("Olá mundo", 0, 10),
        DummySnippet("Segundo bloco", 10, 10),
        DummySnippet("Terceiro bloco", 20, 10),
    ])


@pytest.fixture
def mock_model_loader_service():
    mock = MagicMock()
    mock.model.tokenizer = MagicMock()
    mock.model.tokenizer.encode.side_effect = lambda txt, add_special_tokens=False: [ord(c) for c in txt]
    mock.model.tokenizer.decode.side_effect = lambda ids, skip_special_tokens=True: ''.join(chr(i) for i in ids)
    return mock


@pytest.mark.YoutubeTranscriptSplitterService
class TestYoutubeTranscriptSplitterService:
    def test_split_by_time(self, dummy_transcript, mock_model_loader_service):
        with patch.object(logger, "info"), patch.object(logger, "debug"):
            splitter = YoutubeTranscriptSplitterService(mock_model_loader_service)
            docs = splitter.split_transcript(dummy_transcript, window_size=15, overlap=5, mode="time")
            assert isinstance(docs, list)
            assert all(isinstance(doc, Document) for doc in docs)
            assert len(docs) > 0
            for doc in docs:
                assert "window_start" in doc.metadata
                assert "window_end" in doc.metadata
                assert doc.metadata["video_id"] == "dummy_video_id"

    def test_split_by_tokens(self, dummy_transcript, mock_model_loader_service):
        with patch.object(logger, "info"), patch.object(logger, "debug"):
            splitter = YoutubeTranscriptSplitterService(mock_model_loader_service)
            docs = splitter.split_transcript(dummy_transcript, mode="tokens", tokens_per_chunk=10, token_overlap=2)
            assert isinstance(docs, list)
            assert all(isinstance(doc, Document) for doc in docs)
            assert len(docs) > 0
            for doc in docs:
                assert "window_start" in doc.metadata
                assert "window_end" in doc.metadata
                assert doc.metadata["video_id"] == "dummy_video_id"
                assert "token_count" in doc.metadata

    def test_empty_transcript(self, mock_model_loader_service):
        with patch.object(logger, "info"), patch.object(logger, "debug"):
            empty_transcript = DummyTranscript([])
            splitter = YoutubeTranscriptSplitterService(mock_model_loader_service)
            docs = splitter.split_transcript(empty_transcript, window_size=15, overlap=5, mode="time")
            assert docs == []

    def test_invalid_overlap(self, dummy_transcript, mock_model_loader_service):
        with patch.object(logger, "error"):
            splitter = YoutubeTranscriptSplitterService(mock_model_loader_service)
            with pytest.raises(ValueError):
                splitter.split_transcript(dummy_transcript, window_size=10, overlap=10, mode="time")
            with pytest.raises(ValueError):
                splitter.split_transcript(dummy_transcript, mode="tokens", tokens_per_chunk=5, token_overlap=5)

    def test_no_tokenizer(self, dummy_transcript):
        with patch.object(logger, "error"):
            mock_model_loader_service = MagicMock()
            mock_model_loader_service.model.tokenizer = None
            splitter = YoutubeTranscriptSplitterService(mock_model_loader_service)
            with pytest.raises(RuntimeError):
                splitter.split_transcript(dummy_transcript, mode="tokens", tokens_per_chunk=10, token_overlap=2)
