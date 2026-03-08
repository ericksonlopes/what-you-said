from unittest.mock import MagicMock, patch
import pytest
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

def test_unknown_mode_error(dummy_transcript, mock_model_loader_service):
    with patch.object(logger, "error") as mock_error:
        splitter = YoutubeTranscriptSplitterService(mock_model_loader_service)
        with pytest.raises(ValueError) as exc:
            splitter.split_transcript(dummy_transcript, mode="unknown_mode", tokens_per_chunk=10)
        assert "Unknown splitting mode" in str(exc.value)
        mock_error.assert_called()
        call_args = mock_error.call_args[1]
        assert call_args["context"]["mode"] == "unknown_mode"

