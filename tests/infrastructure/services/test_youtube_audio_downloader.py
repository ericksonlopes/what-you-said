import pytest
from unittest.mock import patch
from src.infrastructure.services.youtube_audio_downloader import AudioDownloader


@pytest.mark.Downloader
class TestAudioDownloader:
    @patch("yt_dlp.YoutubeDL")
    @patch("os.makedirs")
    def test_download_success(self, mock_makedirs, mock_ytdl):
        # Mocking yt_dlp to return a fake filename
        mock_instance = mock_ytdl.return_value.__enter__.return_value
        mock_instance.extract_info.return_value = {"title": "Test Audio", "ext": "webm"}
        mock_instance.prepare_filename.return_value = "temp_audio/Test Audio.webm"

        downloader = AudioDownloader(output_dir="temp_audio")
        result = downloader.download("https://www.youtube.com/watch?v=dummy")

        # In the real code, it changes extension to .mp3
        assert result == "temp_audio/Test Audio.mp3"
        assert mock_instance.extract_info.called
        assert mock_makedirs.called

    @patch("yt_dlp.YoutubeDL")
    def test_download_failure(self, mock_ytdl):
        # Simulating exception during download
        mock_instance = mock_ytdl.return_value.__enter__.return_value
        mock_instance.extract_info.side_effect = Exception("Download error")

        downloader = AudioDownloader()
        result = downloader.download("https://www.youtube.com/watch?v=bad")

        assert result is None
