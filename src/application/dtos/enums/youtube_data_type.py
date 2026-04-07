from enum import Enum


class YoutubeDataType(str, Enum):
    """Type of YouTube data to ingest."""

    VIDEO = "video"
    PLAYLIST = "playlist"
    CHANNEL = "channel"
