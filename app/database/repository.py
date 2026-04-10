"""
Database repository — synchronous CRUD operations.

Mirrors the async database.py from the FastAPI app, using
synchronous SQLAlchemy sessions.
"""
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import func, desc
from app.extensions import db
from app.database.models import AnalysisResult
from app.utils.logger import logger


# ─── Analysis CRUD ────────────────────────────────────────


def save_analysis(
    media_type: str,
    filename: str,
    file_hash: str,
    is_fake: bool,
    confidence: float,
    model_fingerprint: str | None,
    artifact_signatures: list,
    provenance_score: float | None,
    processing_time_ms: float,
    file_size_mb: float,
    resolution: str | None,
    recommendation: str,
    metadata_anomalies: list,
) -> str:
    """Insert an analysis record and return its ID."""
    record_id = str(uuid.uuid4())

    # Serialize artifact signatures
    serialized_artifacts = json.dumps([
        s if isinstance(s, dict) else s
        for s in artifact_signatures
    ])

    record = AnalysisResult(
        id=record_id,
        timestamp=datetime.now(timezone.utc),
        media_type=media_type,
        filename=filename,
        file_hash=file_hash,
        is_fake=is_fake,
        confidence=confidence,
        model_fingerprint=model_fingerprint,
        artifact_signatures_json=serialized_artifacts,
        provenance_score=provenance_score,
        processing_time_ms=processing_time_ms,
        file_size_mb=file_size_mb,
        resolution=resolution,
        recommendation=recommendation,
        metadata_anomalies_json=json.dumps(metadata_anomalies),
    )

    try:
        db.session.add(record)
        db.session.commit()
        logger.info(f"Analysis saved: {record_id}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to save analysis: {e}")
        raise

    return record_id


def get_analysis(record_id: str) -> dict | None:
    """Fetch a single analysis record by ID."""
    record = db.session.get(AnalysisResult, record_id)
    return record.to_dict() if record else None


def list_analyses(
    page: int = 1,
    page_size: int = 20,
    media_type: str | None = None,
    is_fake: bool | None = None,
) -> tuple[list[dict], int]:
    """List analysis records with pagination and filtering."""
    query = AnalysisResult.query
    count_query = db.session.query(func.count(AnalysisResult.id))

    if media_type:
        query = query.filter(AnalysisResult.media_type == media_type)
        count_query = count_query.filter(AnalysisResult.media_type == media_type)

    if is_fake is not None:
        query = query.filter(AnalysisResult.is_fake == is_fake)
        count_query = count_query.filter(AnalysisResult.is_fake == is_fake)

    total = count_query.scalar() or 0

    records = (
        query
        .order_by(desc(AnalysisResult.timestamp))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return [r.to_dict() for r in records], total


def delete_analysis(record_id: str) -> bool:
    """Delete a record by ID. Returns True if deleted."""
    record = db.session.get(AnalysisResult, record_id)
    if not record:
        return False
    db.session.delete(record)
    db.session.commit()
    return True


def get_stats() -> dict:
    """Aggregate statistics across all analysis records."""
    total = db.session.query(func.count(AnalysisResult.id)).scalar() or 0

    fake_count = (
        db.session.query(func.count(AnalysisResult.id))
        .filter(AnalysisResult.is_fake == True)  # noqa: E712
        .scalar() or 0
    )

    avg_conf = (
        db.session.query(func.avg(AnalysisResult.confidence))
        .scalar() or 0.0
    )

    # By media type
    mt_rows = (
        db.session.query(
            AnalysisResult.media_type,
            func.count(AnalysisResult.id).label("count"),
        )
        .group_by(AnalysisResult.media_type)
        .all()
    )
    by_media_type = {row.media_type: row.count for row in mt_rows}

    # By recommendation
    rec_rows = (
        db.session.query(
            AnalysisResult.recommendation,
            func.count(AnalysisResult.id).label("count"),
        )
        .group_by(AnalysisResult.recommendation)
        .all()
    )
    by_recommendation = {row.recommendation: row.count for row in rec_rows}

    real_count = total - fake_count
    return {
        "total_scans": total,
        "fake_count": fake_count,
        "real_count": real_count,
        "fake_percentage": round((fake_count / total * 100) if total > 0 else 0.0, 2),
        "average_confidence": round(float(avg_conf), 4),
        "by_media_type": by_media_type,
        "by_recommendation": by_recommendation,
    }
