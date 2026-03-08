from unittest.mock import patch

import pytest
from youtube_transcript_api import YouTubeTranscriptApi

from src.infrastructure.extractors.youtube_transcript_processor_extractor import YoutubeTranscriptExtractor
from src.infrastructure.extractors.youtube_transcript_processor_extractor import logger


class DummyTranscript:
    def __len__(self):
        return 1


def test_fetch_transcript_success():
    video_id = "dummy_id"
    languages = ["pt"]
    dummy_transcript = DummyTranscript()

    with patch.object(YouTubeTranscriptApi, "fetch") as mock_fetch:
        mock_fetch.return_value = dummy_transcript
        with patch.object(logger, "info"), patch.object(logger, "debug"):
            extractor = YoutubeTranscriptExtractor()
            result = extractor.fetch_transcript(video_id, languages)
            assert result == dummy_transcript
            mock_fetch.assert_called_once_with(video_id=video_id, languages=languages)


def test_fetch_transcript_no_transcript_found():
    video_id = "dummy_id"
    languages = ["pt"]
    with patch.object(YouTubeTranscriptApi, "fetch") as mock_fetch:
        mock_fetch.side_effect = Exception("NoTranscriptFound")
        with patch.object(logger, "info"), patch.object(logger, "error"):
            extractor = YoutubeTranscriptExtractor()
            with pytest.raises(Exception):
                extractor.fetch_transcript(video_id, languages)
