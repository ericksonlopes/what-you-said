import os

import imageio_ffmpeg
import yt_dlp


class AudioDownloader:
    def __init__(self, output_dir: str = "./temp_audio", quality: str = "192"):
        self.output_dir = output_dir
        self.quality = quality
        self._ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

    def download(self, url: str) -> str | None:
        os.makedirs(self.output_dir, exist_ok=True)
        ydl_opts = {
            "format": "bestaudio/best",
            "ffmpeg_location": self._ffmpeg_path,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": self.quality,
                }
            ],
            "outtmpl": f"{self.output_dir}/%(title)s.%(ext)s",
            "quiet": True,
            "no_warnings": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                base_name = ydl.prepare_filename(info)
                final_path = os.path.splitext(base_name)[0] + ".mp3"
                return final_path
        except Exception as e:
            print(f"  [ERROR] Download failed: {e}")
            return None
