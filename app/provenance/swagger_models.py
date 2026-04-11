from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ProvenanceMetadata(BaseModel):
    source: str
    is_original: bool
    creation_date: Optional[str] = None
    software_history: Optional[List[str]] = None
    modification_flags: Optional[List[str]] = None

class ProvenanceReport(BaseModel):
    media_type: str
    file_info: Dict[str, Any]
    metadata_integrity: str
    anomalies: List[str]
    provenance_score: float
    analysis_details: Dict[str, Any]
    recommendation: str