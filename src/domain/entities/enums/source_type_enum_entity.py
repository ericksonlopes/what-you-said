from enum import Enum


class SourceType(Enum):
    """Enum for external sources."""

    YOUTUBE = "youtube"
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"
    MARKDOWN = "markdown"
    HTML = "html"
    ASCII_DOC = "asciidoc"
    LATEX = "latex"
    CSV = "csv"
    IMAGE = "image"
    TXT = "txt"
    OTHER = "other"
    ARTICLE = "article"
    WIKIPEDIA = "wikipedia"
    WEB = "web"
    NOTION = "notion"
