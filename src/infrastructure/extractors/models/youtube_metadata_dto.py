from typing import Optional, List

from pydantic import BaseModel, Field


class YoutubeMetadataDTO(BaseModel):
    video_id: Optional[str] = Field(default=None, description="ID do vídeo do YouTube")
    original_url: Optional[str] = Field(default=None, description="URL original do vídeo")
    title: Optional[str] = Field(default=None, description="Título do vídeo")
    full_title: Optional[str] = Field(default=None, description="Título completo do vídeo", alias="fulltitle")
    description: Optional[str] = Field(default=None, description="Descrição do vídeo")
    duration: Optional[int] = Field(default=None, description="Duração em segundos")
    duration_string: Optional[str] = Field(default=None, description="Duração formatada")
    categories: Optional[List[str]] = Field(default=None, description="Categorias do vídeo")
    tags: Optional[List[str]] = Field(default=None, description="Tags do vídeo")
    channel: Optional[str] = Field(default=None, description="Nome do canal")
    channel_id: Optional[str] = Field(default=None, description="ID do canal")
    url_streaming: Optional[str] = Field(default=None, description="URL para streaming")
    upload_date: Optional[str] = Field(default=None, description="Data de upload")
    language: Optional[str] = Field(default=None, description="Idioma do vídeo")
    is_live: Optional[bool] = Field(default=None, description="Se o vídeo é ao vivo")
    uploader: Optional[str] = Field(default=None, description="Nome do uploader")
    uploader_id: Optional[str] = Field(default=None, description="ID do uploader")
    uploader_url: Optional[str] = Field(default=None, description="URL do uploader")
