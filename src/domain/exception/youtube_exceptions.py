from typing import Optional


class YoutubeException(Exception):
    """Base exception for YouTube-related errors."""

    def __init__(self, message: str, video_id: Optional[str] = None):
        super().__init__(message)
        self.video_id = video_id


class YoutubeVideoPrivateException(YoutubeException):
    """Raised when a YouTube video is private."""

    def __init__(self, video_id: str):
        message = f"The video {video_id} is private and cannot be accessed."
        super().__init__(message, video_id=video_id)


class YoutubeVideoUnplayableException(YoutubeException):
    """Raised when a YouTube video is unplayable (general reasons)."""

    def __init__(self, video_id: str, reason: str = ""):
        message = f"The video {video_id} cannot be played. Reason: {reason}"
        super().__init__(message, video_id=video_id)


class YoutubeTranscriptNotFoundException(YoutubeException):
    """Raised when no transcript is found for a YouTube video."""

    def __init__(
        self,
        video_id: str,
        language: Optional[str] = None,
        available_languages: Optional[list[str]] = None,
    ):
        lang_str = f" in language '{language}'" if language else ""
        avail_str = (
            f" Available languages: {', '.join(available_languages)}."
            if available_languages
            else ""
        )
        message = f"Transcript not found for video {video_id}{lang_str}.{avail_str}"
        super().__init__(message, video_id=video_id)
        self.available_languages = available_languages


class YoutubeTranscriptsDisabledException(YoutubeException):
    """Raised when transcripts are disabled for a YouTube video."""

    def __init__(self, video_id: str):
        message = f"Transcripts are disabled for video {video_id}."
        super().__init__(message, video_id=video_id)


class YoutubeNetworkException(YoutubeException):
    """Raised when there is a network-related error (DNS, connection)."""

    def __init__(self, video_id: str, error_msg: str):
        message = (
            f"Network error while accessing video {video_id}. "
            f"Please check your connection. Details: {error_msg}"
        )
        super().__init__(message, video_id=video_id)


class YoutubeIPBlockedException(YoutubeException):
    """Raised when YouTube is blocking requests from the server's IP."""

    def __init__(self, video_id: str, error_msg: str):
        message = (
            f"YouTube is blocking our requests for video {video_id}. "
            f"Likely IP ban or temporary block. Details: {error_msg}"
        )
        super().__init__(message, video_id=video_id)
