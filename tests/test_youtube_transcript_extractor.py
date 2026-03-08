from unittest.mock import patch

import pytest
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

from src.infrastructure.extractors.youtube_transcript_processor_extractor import YoutubeTranscriptExtractor
from src.infrastructure.extractors.youtube_transcript_processor_extractor import logger


class DummyTranscript:
    def __len__(self):
        return 1


@pytest.mark.YoutubeTranscriptExtractor
class TestYoutubeTranscriptExtractor:
    def test_fetch_transcript_success(self):
        video_id = "dummy_id"
        language = "pt"
        dummy_transcript = DummyTranscript()

        with patch.object(YouTubeTranscriptApi, "fetch") as mock_fetch:
            mock_fetch.return_value = dummy_transcript
            with patch.object(logger, "info"), patch.object(logger, "debug"):
                extractor = YoutubeTranscriptExtractor()
                result = extractor.fetch_transcript(video_id, language)
                assert result == dummy_transcript
                mock_fetch.assert_called_once_with(video_id=video_id, languages=[language])

    def test_fetch_transcript_no_transcript_found(self):
        video_id = "dummy_id"
        language = "pt"
        transcript_data = ""  # Should be a string
        requested_language_codes = [language]
        message = "No transcript found"
        with patch.object(YouTubeTranscriptApi, "fetch") as mock_fetch:
            mock_fetch.side_effect = NoTranscriptFound(transcript_data, requested_language_codes, message)
            with patch.object(logger, "info"), patch.object(logger, "error"):
                extractor = YoutubeTranscriptExtractor()
                with pytest.raises(NoTranscriptFound):
                    extractor.fetch_transcript(video_id, language)

    def test_fetch_transcript_transcripts_disabled(self):
        video_id = "dummy_id"
        language = "pt"
        with patch.object(YouTubeTranscriptApi, "fetch") as mock_fetch:
            mock_fetch.side_effect = TranscriptsDisabled("Transcripts disabled")
            with patch.object(logger, "info"), patch.object(logger, "warning"):
                extractor = YoutubeTranscriptExtractor()
                with pytest.raises(TranscriptsDisabled):
                    extractor.fetch_transcript(video_id, language)

    def test_fetch_transcript_generic_error(self):
        video_id = "dummy_id"
        language = "pt"
        with patch.object(YouTubeTranscriptApi, "fetch") as mock_fetch:
            mock_fetch.side_effect = Exception("Generic error")
            with patch.object(logger, "info"), patch.object(logger, "error"):
                extractor = YoutubeTranscriptExtractor()
                with pytest.raises(Exception):
                    extractor.fetch_transcript(video_id, language)
