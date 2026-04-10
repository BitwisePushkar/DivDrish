"""
SQLAlchemy ORM models.

Maintains schema compatibility with the existing FastAPI database.
"""
import uuid
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


class AnalysisResult(db.Model):
    """Stores every detection run for history/audit."""

    __tablename__ = "analysis_results"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    media_type = db.Column(db.String(10), nullable=False)
    filename = db.Column(db.String(512), nullable=False)
    file_hash = db.Column(db.String(64), nullable=False)
    is_fake = db.Column(db.Boolean, nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    model_fingerprint = db.Column(db.String(64), nullable=True)
    artifact_signatures_json = db.Column(db.Text, nullable=True)
    provenance_score = db.Column(db.Float, nullable=True)
    processing_time_ms = db.Column(db.Float, nullable=False)
    file_size_mb = db.Column(db.Float, nullable=False)
    resolution = db.Column(db.String(32), nullable=True)
    recommendation = db.Column(db.String(16), nullable=False)
    metadata_anomalies_json = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "media_type": self.media_type,
            "filename": self.filename,
            "file_hash": self.file_hash,
            "is_fake": self.is_fake,
            "confidence": self.confidence,
            "model_fingerprint": self.model_fingerprint,
            "artifact_signatures_json": self.artifact_signatures_json,
            "provenance_score": self.provenance_score,
            "processing_time_ms": self.processing_time_ms,
            "file_size_mb": self.file_size_mb,
            "resolution": self.resolution,
            "recommendation": self.recommendation,
            "metadata_anomalies_json": self.metadata_anomalies_json,
        }


class User(db.Model):
    """User model for authentication."""

    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    api_key = db.Column(db.String(64), unique=True, nullable=True, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=True, onupdate=lambda: datetime.now(timezone.utc))

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "api_key": self.api_key,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
