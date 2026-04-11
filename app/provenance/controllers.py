from app.services.metadata_analyzer import analyze_metadata

def analyze_provenance(file_path: str, filename: str, media_type: str) -> dict:
    result = analyze_metadata(file_path, media_type)
    score = result["provenance_score"]
    if score >= 0.75:
        risk_level = "LOW"
    elif score >= 0.45:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"
    return {
        "filename": filename,
        "media_type": media_type,
        "provenance_score": score,
        "metadata_anomalies": result["anomalies"],
        "metadata_extracted": result["metadata_extracted"],
        "ai_generation_indicators": result.get("ai_generation_indicators", []),
        "risk_level": risk_level,
    }