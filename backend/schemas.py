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


class RelicUpdate(BaseModel):
    """Relic update schema."""
    name: Optional[str] = None
    content_type: Optional[str] = None
    language_hint: Optional[str] = None
    access_level: Optional[Literal["public", "private"]] = None
    expires_in: Optional[str] = None  # "1h", "24h", "7d", "30d", or "never"
    tags: Optional[List[str]] = None


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
    access_count: int
    bookmark_count: int
    can_edit: bool = False
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


class ReportCreate(BaseModel):
    """Report creation schema."""
    relic_id: str
    reason: str


class ReportResponse(BaseModel):
    """Report response schema."""
    id: str
    relic_id: str
    reason: str
    created_at: datetime
    relic_name: Optional[str] = None  # Enriched field for admin view

    class Config:
        from_attributes = True


class CommentBase(BaseModel):
    """Base comment schema."""
    content: str
    line_number: int


class CommentCreate(CommentBase):
    """Comment creation schema."""
    parent_id: Optional[str] = None


class CommentUpdate(BaseModel):
    """Comment update schema."""
    content: str


class CommentResponse(CommentBase):
    """Comment response schema."""
    id: str
    relic_id: str
    client_id: Optional[str] = None
    author_name: Optional[str] = None
    created_at: datetime
    parent_id: Optional[str] = None

    class Config:
        from_attributes = True


class ClientNameUpdate(BaseModel):
    """Schema for updating client name."""
    name: str
