from pydantic import BaseModel, Field
from typing import List, Optional, Any

class HistoryQuery(BaseModel):
    page: Optional[int] = Field(1, description="Page number")
    page_size: Optional[int] = Field(20, description="Records per page (max 100)")
    media_type: Optional[str] = Field(None, description="Filter by media type (image, video, audio)")
    is_fake: Optional[str] = Field(None, description="Filter by detection result (true, false)")

class HistoryRecord(BaseModel):
    id: str
    media_type: str
    filename: str
    is_fake: bool
    confidence: float
    created_at: str
    processing_time_ms: int
    recommendation: str

class PaginatedHistory(BaseModel):
    items: List[HistoryRecord]
    total: int
    page: int
    pages: int
    has_next: bool
    has_prev: bool

class AnalysisStats(BaseModel):
    total_analyses: int
    fake_detected: int
    real_detected: int
    average_confidence: float
    by_media_type: dict