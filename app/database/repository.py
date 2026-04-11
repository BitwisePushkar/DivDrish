import json
import uuid
import os
from datetime import datetime, timezone
from sqlalchemy import func, desc
from app.extensions import db
from app.database.models import AnalysisResult
from app.utils.logger import logger
from app.utils.s3_service import s3_service

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
    user_id: str | None = None,
    temp_path: str | None = None,
) -> str:
    record_id = str(uuid.uuid4())
    media_url = None
    if temp_path and os.path.exists(temp_path):
        safe_user_id = user_id or "anonymous"
        object_name = f"history/{safe_user_id}/{record_id}_{filename}"
        media_url = s3_service.upload_file(temp_path, object_name)
    serialized_artifacts = json.dumps([
        s if isinstance(s, dict) else s
        for s in artifact_signatures
    ])
    record = AnalysisResult(
        id=record_id,
        user_id=user_id,
        timestamp=datetime.now(timezone.utc),
        media_type=media_type,
        filename=filename,
        file_hash=file_hash,
        media_url=media_url,
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
        logger.info(f"Analysis saved: {record_id}{' with S3 URL' if media_url else ''}")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to save analysis: {e}")
        raise
    return record_id

def get_analysis(record_id: str, user_id: str | None = None) -> dict | None:
    record = db.session.get(AnalysisResult, record_id)
    if not record:
        return None
    if user_id and record.user_id != user_id:
        return None
    return record.to_dict()

def list_analyses(
    page: int = 1,
    page_size: int = 20,
    media_type: str | None = None,
    is_fake: bool | None = None,
    user_id: str | None = None,
) -> tuple[list[dict], int]:
    query = AnalysisResult.query
    count_query = db.session.query(func.count(AnalysisResult.id))
    if user_id:
        query = query.filter(AnalysisResult.user_id == user_id)
        count_query = count_query.filter(AnalysisResult.user_id == user_id)
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

def delete_analysis(record_id: str, user_id: str | None = None) -> bool:
    record = db.session.get(AnalysisResult, record_id)
    if not record:
        return False
    if user_id and record.user_id != user_id:
        return False
    db.session.delete(record)
    db.session.commit()
    return True

def get_stats(user_id: str | None = None) -> dict:
    base_filter = []
    if user_id:
        base_filter.append(AnalysisResult.user_id == user_id)
    total = db.session.query(func.count(AnalysisResult.id)).filter(*base_filter).scalar() or 0
    fake_count = (
        db.session.query(func.count(AnalysisResult.id))
        .filter(AnalysisResult.is_fake == True, *base_filter)  # noqa: E712
        .scalar() or 0
    )
    avg_conf = (
        db.session.query(func.avg(AnalysisResult.confidence))
        .filter(*base_filter)
        .scalar() or 0.0
    )
    mt_rows = (
        db.session.query(
            AnalysisResult.media_type,
            func.count(AnalysisResult.id).label("count"),
        )
        .filter(*base_filter)
        .group_by(AnalysisResult.media_type)
        .all()
    )
    by_media_type = {row.media_type: row.count for row in mt_rows}
    rec_rows = (
        db.session.query(
            AnalysisResult.recommendation,
            func.count(AnalysisResult.id).label("count"),
        )
        .filter(*base_filter)
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