from pydantic import BaseModel, Field
from typing import List, Optional
from flask_openapi3 import FileStorage

class FileBody(BaseModel):
    file: FileStorage

class BatchFileBody(BaseModel):
    files: List[FileStorage]

class DetectionResult(BaseModel):
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
    total_files: int
    processed: int
    fake_count: int
    average_confidence: float
    results: List[dict]

class TaskStatus(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None

class AsyncStartedResponse(BaseModel):
    task_id: str
    status: str
    message: str
    total_files: Optional[int] = None