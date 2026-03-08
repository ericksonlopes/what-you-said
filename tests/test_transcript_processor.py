from unittest.mock import patch

import pytest

from src.infrastructure.services.transcript_processor import TranscriptProcessor


class DummyTranscript:
    def __len__(self):
        return 1


def test_fetch_transcript_success():
    video_id = "dummy_id"
    languages = ["pt"]
    dummy_transcript = DummyTranscript()

    with patch("src.infrastructure.services.transcript_processor.YouTubeTranscriptApi") as mock_api:
        mock_instance = mock_api.return_value
        mock_instance.fetch.return_value = dummy_transcript
        with patch("src.infrastructure.services.transcript_processor.logger"):
            processor = TranscriptProcessor()
            result = processor.fetch_transcript(video_id, languages)
            assert result == dummy_transcript
            mock_instance.fetch.assert_called_once_with(video_id=video_id, languages=languages)


def test_fetch_transcript_no_transcript_found():
    video_id = "dummy_id"
    languages = ["pt"]
    with patch("src.infrastructure.services.transcript_processor.YouTubeTranscriptApi") as mock_api:
        mock_instance = mock_api.return_value
        mock_instance.fetch.side_effect = Exception("NoTranscriptFound")
        with patch("src.infrastructure.services.transcript_processor.logger"):
            processor = TranscriptProcessor()
            with pytest.raises(Exception):
                processor.fetch_transcript(video_id, languages)
