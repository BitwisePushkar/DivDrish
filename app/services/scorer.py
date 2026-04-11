from app.models.base_detector import RawDetection

def _get_config():
    from app.config.settings import get_config
    return get_config()

def compute_final_score(raw: RawDetection, media_type: str) -> dict:
    config = _get_config()
    threshold = getattr(config, f"{media_type.upper()}_THRESHOLD")
    base = raw.confidence
    artifact_boost = 0.0
    if raw.artifact_scores:
        high = [v for v in raw.artifact_scores.values() if v > 0.6]
        artifact_boost = min(len(high) * 0.03, 0.12)
    final = min(base + artifact_boost, 1.0)
    is_fake = final >= threshold
    if final >= 0.85:
        recommendation = "FLAG"
    elif final >= 0.60:
        recommendation = "REVIEW"
    else:
        recommendation = "CLEAR"
    return {
        "confidence":     round(final, 4),
        "is_fake":        is_fake,
        "recommendation": recommendation,
        "threshold_used": threshold,
    }