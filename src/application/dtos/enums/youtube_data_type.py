from enum import Enum


class YoutubeDataType(Enum):
    """Type of YouTube data to ingest."""

    VIDEO = "video"
    PLAYLIST = "playlist"
