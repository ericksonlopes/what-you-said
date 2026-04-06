from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from src.domain.entities.enums.search_mode_enum import SearchMode


class SearchRequest(BaseModel):
    query: str = Field(
        ...,
        description="A query string to search for",
        json_schema_extra={"examples": ["Quem é o palestrante?"]},
    )
    top_k: int = Field(default=5, ge=1, le=50)
    subject_ids: Optional[List[Union[str, UUID]]] = None
    subject_name: Optional[str] = None
    search_mode: SearchMode = Field(
        default=SearchMode.HYBRID,
        description="Search strategy: semantic (vector), bm25 (keyword), or hybrid",
    )
    re_rank: bool = Field(
        default=True,
        description="Enable re-ranking of search results",
    )


class ChunkResultSchema(BaseModel):
    id: UUID
    content_source_id: Optional[UUID] = None
    content: Optional[str] = None
    external_source: Optional[str] = None
    source_type: Optional[str] = None
    tokens_count: Optional[int] = None
    language: Optional[str] = None
    embedding_model: Optional[str] = None
    subject_id: Optional[UUID] = None
    index: Optional[int] = None
    created_at: Optional[datetime] = None
    score: Optional[float] = None
    extra: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class SearchResponse(BaseModel):
    query: str
    results: List[ChunkResultSchema]
    total_count: int
    search_mode: Optional[str] = None
