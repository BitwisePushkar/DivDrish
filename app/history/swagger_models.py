"""
Pydantic models for the History module Swagger documentation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Any


class HistoryQuery(BaseModel):
    """Query parameters for listing history."""
    page: Optional[int] = Field(1, description="Page number")
    page_size: Optional[int] = Field(20, description="Records per page (max 100)")
    media_type: Optional[str] = Field(None, description="Filter by media type (image, video, audio)")
    is_fake: Optional[str] = Field(None, description="Filter by detection result (true, false)")


class HistoryRecord(BaseModel):
    """Individual analysis record schema."""
    id: str
    media_type: str
    filename: str
    is_fake: bool
    confidence: float
    created_at: str
    processing_time_ms: int
    recommendation: str


class PaginatedHistory(BaseModel):
    """Schema for paginated history response."""
    items: List[HistoryRecord]
    total: int
    page: int
    pages: int
    has_next: bool
    has_prev: bool


class AnalysisStats(BaseModel):
    """Schema for overall statistics."""
    total_analyses: int
    fake_detected: int
    real_detected: int
    average_confidence: float
    by_media_type: dict
