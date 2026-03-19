from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SubjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    icon: Optional[str] = None
    external_ref: Optional[str] = None


class SubjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    icon: Optional[str] = None


class SubjectResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    sourceCount: int = Field(0, validation_alias="source_count")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
