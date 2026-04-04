from enum import Enum


class SourceType(Enum):
    """Enum for external sources."""

    YOUTUBE = "youtube"
    WEB = "web"
    PDF = "pdf"
    DOCX = "docx"
    CSV = "csv"
    IMAGE = "image"
    TXT = "txt"
    HTML = "html"
    PPTX = "pptx"
    XLSX = "xlsx"
    MARKDOWN = "markdown"
    ASCII_DOC = "asciidoc"
    LATEX = "latex"
    AUDIO = "audio"
    OTHER = "other"
