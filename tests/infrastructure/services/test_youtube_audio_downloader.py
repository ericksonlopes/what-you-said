from unittest.mock import patch

import pytest

from src.infrastructure.extractors.youtube_extractor import YoutubeExtractor


@pytest.mark.Downloader
class TestYoutubeExtractorDownload:
    @patch("src.infrastructure.extractors.youtube_extractor.YoutubeExtractor._validate_mp3_file")
    @patch("src.infrastructure.extractors.youtube_extractor.YoutubeDL")
    @patch("os.makedirs")
    def test_download_success(self, mock_makedirs, mock_ytdl, mock_validate):
        # Mocking yt_dlp to return a fake filename
        mock_instance = mock_ytdl.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = {"title": "Test Audio", "ext": "webm"}
        mock_instance.prepare_filename.return_value = "temp_audio/Test Audio.webm"

        extractor = YoutubeExtractor()
        result = extractor.download_audio("https://www.youtube.com/watch?v=dummy", output_dir="temp_audio")

        # In the code, it changes extension to .mp3 using Path.with_suffix
        assert result == "temp_audio\\Test Audio.mp3" or result == "temp_audio/Test Audio.mp3"
        assert mock_instance.extract_info.called
        assert mock_makedirs.called

    @patch("src.infrastructure.extractors.youtube_extractor.YoutubeDL")
    def test_download_failure(self, mock_ytdl):
        # Simulating exception during download
        mock_instance = mock_ytdl.return_value.__enter__.return_value
        mock_instance.extract_info.side_effect = Exception("Download error")

        extractor = YoutubeExtractor()
        result = extractor.download_audio("https://www.youtube.com/watch?v=bad")

        assert result is None
