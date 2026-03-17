from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from src.infrastructure.services.youtube_data_process_service import (
    YoutubeDataProcessService,
    logger,
)


@pytest.fixture
def dummy_yt_extractor():
    mock = MagicMock()
    mock.extract_transcript.return_value = []
    return mock


class DummySnippet:
    def __init__(self, text, start, duration):
        self.text = text
        self.start = start
        self.duration = duration


class DummyTranscript(list):
    video_id = "dummy_video_id"


@pytest.fixture
def dummy_transcript():
    return DummyTranscript(
        [
            DummySnippet("Olá mundo", 0, 10),
            DummySnippet("Segundo bloco", 10, 10),
            DummySnippet("Terceiro bloco", 20, 10),
        ]
    )


@pytest.fixture
def mock_model_loader_service():
    mock = MagicMock()
    mock.model.tokenizer = MagicMock()
    mock.model.tokenizer.encode.side_effect = lambda txt, add_special_tokens=False: [
        ord(c) for c in txt
    ]
    mock.model.tokenizer.decode.side_effect = lambda ids, skip_special_tokens=True: (
        "".join(chr(i) for i in ids)
    )
    return mock


@pytest.mark.YoutubeDataProcessService
class TestYoutubeDataService:
    def test_split_by_time(
        self, dummy_transcript, mock_model_loader_service, dummy_yt_extractor
    ):
        dummy_yt_extractor.extract_transcript.return_value = dummy_transcript
        with patch.object(logger, "info"), patch.object(logger, "debug"):
            splitter = YoutubeDataProcessService(
                mock_model_loader_service, dummy_yt_extractor
            )
            docs = splitter.split_transcript(
                mode="time", time_window_size=30, time_overlap=5
            )
            assert isinstance(docs, list)
            assert all(isinstance(doc, Document) for doc in docs)
            assert len(docs) > 0
            for doc in docs:
                assert "window_start" in doc.metadata
                assert "window_end" in doc.metadata
                assert doc.metadata["video_id"] == "dummy_video_id"

    def test_split_by_tokens(
        self, dummy_transcript, mock_model_loader_service, dummy_yt_extractor
    ):
        dummy_yt_extractor.extract_transcript.return_value = dummy_transcript
        with patch.object(logger, "info"), patch.object(logger, "debug"):
            splitter = YoutubeDataProcessService(
                mock_model_loader_service, dummy_yt_extractor
            )
            docs = splitter.split_transcript(
                mode="tokens", tokens_per_chunk=10, tokens_overlap=2
            )
            assert isinstance(docs, list)
            assert all(isinstance(doc, Document) for doc in docs)
            assert len(docs) > 0
            for doc in docs:
                assert "window_start" in doc.metadata
                assert "window_end" in doc.metadata
                assert doc.metadata["video_id"] == "dummy_video_id"
                assert "token_count" in doc.metadata

    def test_empty_transcript(self, mock_model_loader_service, dummy_yt_extractor):
        with patch.object(logger, "info"), patch.object(logger, "debug"):
            splitter = YoutubeDataProcessService(
                mock_model_loader_service, dummy_yt_extractor
            )
            docs = splitter.split_transcript(
                mode="time", time_window_size=30, time_overlap=5
            )
            assert docs == []

    def test_invalid_overlap(
        self, dummy_transcript, mock_model_loader_service, dummy_yt_extractor
    ):
        dummy_yt_extractor.extract_transcript.return_value = dummy_transcript
        with patch.object(logger, "error"):
            splitter = YoutubeDataProcessService(
                mock_model_loader_service, dummy_yt_extractor
            )
            with pytest.raises(ValueError):
                splitter.split_transcript(
                    mode="time", time_window_size=30, time_overlap=40
                )
            with pytest.raises(ValueError):
                splitter.split_transcript(
                    mode="tokens", tokens_per_chunk=5, tokens_overlap=10
                )

    def test_no_tokenizer(self, dummy_transcript, dummy_yt_extractor):
        dummy_yt_extractor.extract_transcript.return_value = dummy_transcript
        with patch.object(logger, "error"):
            mock_model_loader_service = MagicMock()
            mock_model_loader_service.model.tokenizer = None
            splitter = YoutubeDataProcessService(
                mock_model_loader_service, dummy_yt_extractor
            )
            with pytest.raises(RuntimeError):
                splitter.split_transcript(
                    mode="tokens", tokens_per_chunk=10, tokens_overlap=2
                )

    def test_encode_typeerror_fallback(
        self, dummy_transcript, mock_model_loader_service, dummy_yt_extractor
    ):
        dummy_yt_extractor.extract_transcript.return_value = dummy_transcript

        def encode_side_effect(txt, add_special_tokens=None):
            if add_special_tokens is not None:
                raise TypeError("unexpected argument")
            return [ord(c) for c in txt]

        mock_model_loader_service.model.tokenizer.encode.side_effect = (
            encode_side_effect
        )
        splitter = YoutubeDataProcessService(
            mock_model_loader_service, dummy_yt_extractor
        )
        docs = splitter.split_transcript(
            mode="tokens", tokens_per_chunk=10, tokens_overlap=2
        )
        assert isinstance(docs, list)
        assert all(isinstance(doc, Document) for doc in docs)
        assert len(docs) > 0
        for doc in docs:
            assert "window_start" in doc.metadata
            assert "window_end" in doc.metadata
            assert doc.metadata["video_id"] == "dummy_video_id"
            assert "token_count" in doc.metadata

    def test_tokenize_skips_empty_snippet(
        self, mock_model_loader_service, dummy_yt_extractor
    ):
        class EmptySnippet:
            text = ""
            start = 0
            duration = 0

        transcript = [EmptySnippet()]
        splitter = YoutubeDataProcessService(
            mock_model_loader_service, dummy_yt_extractor
        )
        with patch.object(logger, "debug") as mock_debug:
            splitter._tokenize_transcript(
                transcript, mock_model_loader_service.model.tokenizer, {}
            )
            mock_debug.assert_any_call(
                "Skipping empty snippet", context={"snippet_index": 0}
            )

    def test_decode_typeerror_and_attributeerror(
        self, mock_model_loader_service, dummy_yt_extractor
    ):
        splitter = YoutubeDataProcessService(
            mock_model_loader_service, dummy_yt_extractor
        )
        chunk_ids = [65, 66]
        transcript = [DummySnippet("A", 0, 1)]

        def decode_typeerror(ids, *args, **kwargs):
            if kwargs.get("skip_special_tokens", False):
                raise TypeError("unexpected argument")
            return "decoded"

        mock_model_loader_service.model.tokenizer.decode.side_effect = decode_typeerror
        docs = splitter._create_token_chunks(
            chunk_ids,
            [{"start": 0, "end": 1, "snippet_index": 0}] * len(chunk_ids),
            len(chunk_ids),
            len(chunk_ids),
            transcript,
            {},
        )
        assert docs[0].page_content == "decoded"

        def decode_attributeerror(ids, *args, **kwargs):
            raise AttributeError("no decode")

        mock_model_loader_service.model.tokenizer.decode.side_effect = (
            decode_attributeerror
        )
        docs = splitter._create_token_chunks(
            chunk_ids,
            [{"start": 0, "end": 1, "snippet_index": 0}] * len(chunk_ids),
            len(chunk_ids),
            len(chunk_ids),
            transcript,
            {},
        )
        assert docs[0].page_content == str(chunk_ids)

    def test_create_token_chunks_empty_meta(
        self, mock_model_loader_service, dummy_yt_extractor
    ):
        import math

        splitter = YoutubeDataProcessService(
            mock_model_loader_service, dummy_yt_extractor
        )
        token_ids = [65, 66]
        token_meta = []
        transcript = [DummySnippet("A", 0, 1)]
        docs = splitter._create_token_chunks(
            token_ids, token_meta, len(token_ids), len(token_ids), transcript, {}
        )
        assert math.isclose(docs[0].metadata["window_start"], 0.0)
        assert math.isclose(docs[0].metadata["window_end"], 0.0)

    def test_unknown_mode_error(
        self, mock_model_loader_service, dummy_yt_extractor, dummy_transcript
    ):
        dummy_yt_extractor.extract_transcript.return_value = dummy_transcript
        with patch.object(logger, "error") as mock_error:
            splitter = YoutubeDataProcessService(
                mock_model_loader_service, dummy_yt_extractor
            )
            with pytest.raises(ValueError) as exc:
                splitter.split_transcript(mode="unknown_mode", tokens_per_chunk=10)  # type: ignore
            assert "Unknown splitting mode" in str(exc.value)
            mock_error.assert_called()
            call_args = mock_error.call_args[1]
            assert call_args["context"]["mode"] == "unknown_mode"
