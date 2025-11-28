"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime




class TagBase(BaseModel):
    """Base tag schema."""
    name: str


class TagResponse(TagBase):
    """Tag response schema."""
    id: str

    class Config:
        from_attributes = True


class RelicBase(BaseModel):
    """Base relic schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    language_hint: Optional[str] = None
    access_level: Literal["public", "private"] = "public"
    password: Optional[str] = None
    expires_in: Optional[str] = None  # "1h", "24h", "7d", "30d", or None
    tags: List[str] = []


class RelicCreate(RelicBase):
    """Relic creation schema."""
    content_type: Optional[str] = "text/plain"


class RelicFork(BaseModel):
    """Relic fork schema."""
    name: Optional[str] = None


class RelicResponse(BaseModel):
    """Relic response schema."""
    id: str
    name: Optional[str]
    description: Optional[str]
    content_type: str
    language_hint: Optional[str]
    size_bytes: int
    fork_of: Optional[str]
    access_level: Literal["public", "private"]
    created_at: datetime
    expires_at: Optional[datetime]
    deleted_at: Optional[datetime]
    access_count: int
    tags: List[TagResponse] = []

    class Config:
        from_attributes = True
        extra = "ignore"


class RelicListResponse(BaseModel):
    """Relic list response schema."""
    relics: List[RelicResponse]




class PreviewResponse(BaseModel):
    """Generic preview response."""
    type: str
    metadata: dict
    preview: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Error response schema."""
    detail: str
    error_code: Optional[str] = None
