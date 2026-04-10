"""
Pydantic models for the Detection module Swagger documentation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from flask_openapi3 import FileStorage


class FileBody(BaseModel):
    """Body for single file upload."""
    file: FileStorage


class BatchFileBody(BaseModel):
    """Body for multiple file uploads (batch)."""
    files: List[FileStorage]


class DetectionResult(BaseModel):
    """Schema for a single detection result."""
    media_type: str
    is_fake: bool
    confidence: float
    recommendation: str
    processing_time_ms: int
    file_size_mb: float
    resolution: Optional[str] = None
    model_fingerprint: Optional[str] = None
    artifact_signatures: Optional[List[str]] = None
    metadata_anomalies: Optional[List[str]] = None
    provenance_score: Optional[float] = None


class BatchResult(BaseModel):
    """Schema for a batch detection result."""
    total_files: int
    processed: int
    fake_count: int
    average_confidence: float
    results: List[dict]


class TaskStatus(BaseModel):
    """Schema for async task status."""
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


class AsyncStartedResponse(BaseModel):
    """Schema for async task initiation response."""
    task_id: str
    status: str
    message: str
    total_files: Optional[int] = None
