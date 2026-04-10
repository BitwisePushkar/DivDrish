from pydantic import BaseModel, Field
from typing import List, Optional

class CommunityPostCreate(BaseModel):
    analysis_id: str = Field(description="The ID of the analysis result linking to this post.")
    title: Optional[str] = Field(None, description="Optional title for the post.")
    description: Optional[str] = Field(None, description="Optional description for the post.")

class PaginationQuery(BaseModel):
    page: Optional[int] = 1
    page_size: Optional[int] = 20

class AuthorInfo(BaseModel):
    username: str

class AnalysisSummary(BaseModel):
    media_type: str
    is_fake: bool
    confidence: float
    recommendation: str
    file_hash: str
    media_url: Optional[str]

class CommunityPostResponse(BaseModel):
    id: str
    title: Optional[str]
    description: Optional[str]
    created_at: str
    author: AuthorInfo
    analysis: Optional[AnalysisSummary]

class PaginatedCommunityPosts(BaseModel):
    items: List[CommunityPostResponse]
    total: int
    page: int
    page_size: int
