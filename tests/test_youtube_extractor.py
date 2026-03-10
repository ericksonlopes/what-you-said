from unittest.mock import patch

import pytest
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

from src.config.logger import Logger
from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor

logger = Logger()


class DummyTranscript:
    def __len__(self):
        return 1


@pytest.mark.YoutubeExtractor
class TestYoutubeExtractor:
    def test_extract_transcript_success(self):
        video_id = "dummy_id"
        dummy_transcript = DummyTranscript()

        with patch.object(YouTubeTranscriptApi, "fetch") as mock_fetch:
            mock_fetch.return_value = dummy_transcript
            with patch.object(logger, "info"), patch.object(logger, "debug"):
                extractor = YoutubeExtractor(video_id)
                result = extractor.extract_transcript()
                assert result == dummy_transcript
                mock_fetch.assert_called_once_with(video_id=video_id, languages=[extractor.language])

    def test_extract_transcript_no_transcript_found(self):
        video_id = "dummy_id"
        transcript_data = ""  # Should be a string
        requested_language_codes = ["pt"]
        message = "No transcript found"
        with patch.object(YouTubeTranscriptApi, "fetch") as mock_fetch:
            mock_fetch.side_effect = NoTranscriptFound(transcript_data, requested_language_codes, message)
            with patch.object(logger, "info"), patch.object(logger, "error"):
                extractor = YoutubeExtractor(video_id)
                with pytest.raises(NoTranscriptFound):
                    extractor.extract_transcript()

    def test_extract_transcript_transcripts_disabled(self):
        video_id = "dummy_id"
        with patch.object(YouTubeTranscriptApi, "fetch") as mock_fetch:
            mock_fetch.side_effect = TranscriptsDisabled("Transcripts disabled")
            with patch.object(logger, "info"), patch.object(logger, "warning"):
                extractor = YoutubeExtractor(video_id)
                with pytest.raises(TranscriptsDisabled):
                    extractor.extract_transcript()

    def test_extract_transcript_generic_error(self):
        video_id = "dummy_id"
        with patch.object(YouTubeTranscriptApi, "fetch") as mock_fetch:
            mock_fetch.side_effect = Exception("Generic error")
            with patch.object(logger, "info"), patch.object(logger, "error"):
                extractor = YoutubeExtractor(video_id)
                with pytest.raises(Exception):
                    extractor.extract_transcript()

    def test_extract_metadata_success(self):
        video_id = "dummy_id"
        dummy_info = {
            "original_url": "https://youtube.com/watch?v=dummy_id",
            "title": "Dummy Title",
            "fulltitle": "Dummy Full Title",
            "description": "Dummy Description",
            "duration": 123,
            "duration_string": "2:03",
            "categories": ["Education"],
            "tags": ["test", "dummy"],
            "channel": "Dummy Channel",
            "channel_id": "UCdummy",
            "url_streaming": "https://streaming.url",
            "upload_date": "20260101",
            "language": "en",
            "is_live": False,
            "uploader": "Dummy Uploader",
            "uploader_id": "uploader_dummy",
            "uploader_url": "https://youtube.com/uploader_dummy"
        }
        # Patch YoutubeDL in the correct module
        with patch("src.infrastructure.extractors.youtube_extractor.YoutubeDL") as mock_ytdlp:
            mock_instance = mock_ytdlp.return_value.__enter__.return_value
            mock_instance.extract_info.return_value = dummy_info
            with patch.object(logger, "info"):
                extractor = YoutubeExtractor(video_id)
                metadata = extractor.extract_metadata()
                assert metadata.video_id == video_id
                assert metadata.title == dummy_info["title"]
                assert metadata.full_title == dummy_info["fulltitle"]
                assert metadata.description == dummy_info["description"]
                assert metadata.duration == dummy_info["duration"]
                assert metadata.tags == dummy_info["tags"]
                assert metadata.channel == dummy_info["channel"]
                assert metadata.is_live == dummy_info["is_live"]
                assert metadata.uploader == dummy_info["uploader"]
                assert metadata.uploader_id == dummy_info["uploader_id"]
                assert metadata.uploader_url == dummy_info["uploader_url"]

    def test_extract_metadata_error(self):
        video_id = "dummy_id"
        with patch("yt_dlp.YoutubeDL") as mock_ytdlp:
            mock_instance = mock_ytdlp.return_value.__enter__.return_value
            mock_instance.extract_info.side_effect = Exception("Extraction failed")
            with patch.object(logger, "info"), patch.object(logger, "error"):
                extractor = YoutubeExtractor(video_id)
                metadata = extractor.extract_metadata()
                assert metadata.video_id == video_id

                assert metadata.title is None
                assert metadata.full_title is None
                assert metadata.description is None
                assert metadata.duration is None
                assert metadata.tags is None
                assert metadata.channel is None
                assert metadata.is_live is None
                assert metadata.uploader is None
                assert metadata.uploader_id is None
                assert metadata.uploader_url is None
