"""
Detection controllers — orchestrate ML pipeline per media type.

These are pure functions that take a file path and return result dicts.
They can be called synchronously from routes or from Celery tasks.
"""
import os
import time

from app.models.image_detector import ImageDetector
from app.models.video_detector import VideoDetector
from app.models.audio_detector import AudioDetector
from app.services.artifact_scanner import build_artifact_list
from app.services.fingerprinter import fingerprint_model
from app.services.scorer import compute_final_score
from app.services.metadata_analyzer import analyze_metadata
from app.utils.hasher import sha256_file
from app.utils.logger import logger

# ─── Singleton detectors (loaded once, reused) ───────────

_image_detector = ImageDetector()
_video_detector = VideoDetector()
_audio_detector = AudioDetector()


def get_detectors() -> dict:
    """Return detector registry for health checks."""
    return {
        "image": _image_detector,
        "video": _video_detector,
        "audio": _audio_detector,
    }


def process_image(file_path: str, filename: str) -> dict:
    """Run full image detection pipeline. Returns result dict."""
    t0 = time.time()

    file_hash = sha256_file(file_path)
    raw = _image_detector.predict(file_path)
    scores = compute_final_score(raw, "image")
    provenance = analyze_metadata(file_path, "image")
    artifacts = build_artifact_list(raw.artifact_scores)
    fp = fingerprint_model(raw.artifact_scores)
    file_size = round(os.path.getsize(file_path) / 1024 / 1024, 3)
    resolution = f"{raw.metadata.get('width')}x{raw.metadata.get('height')}"
    proc_time = round((time.time() - t0) * 1000, 1)

    result = {
        "media_type": "image",
        "is_fake": scores["is_fake"],
        "confidence": scores["confidence"],
        "model_fingerprint": fp,
        "artifact_signatures": artifacts,
        "frame_analysis": None,
        "processing_time_ms": proc_time,
        "file_size_mb": file_size,
        "resolution": resolution,
        "metadata_anomalies": provenance["anomalies"],
        "ai_generation_indicators": provenance.get("ai_generation_indicators", []),
        "provenance_score": provenance["provenance_score"],
        "recommendation": scores["recommendation"],
    }

    # DB persistence metadata
    result["_db_meta"] = {
        "filename": filename,
        "file_hash": file_hash,
    }

    return result


def process_video(file_path: str, filename: str) -> dict:
    """Run full video detection pipeline. Returns result dict."""
    t0 = time.time()

    file_hash = sha256_file(file_path)
    raw = _video_detector.predict(file_path)
    scores = compute_final_score(raw, "video")
    provenance = analyze_metadata(file_path, "video")
    artifacts = build_artifact_list(raw.artifact_scores)
    fp = fingerprint_model(raw.artifact_scores)
    file_size = round(os.path.getsize(file_path) / 1024 / 1024, 3)
    resolution = raw.metadata.get("resolution", "")
    proc_time = round((time.time() - t0) * 1000, 1)

    frame_results = [
        {
            "frame_index": f["frame"],
            "timestamp_sec": f["ts"],
            "confidence": f["score"],
            "face_detected": f["face"],
        }
        for f in raw.metadata.get("frame_details", [])
    ]

    result = {
        "media_type": "video",
        "is_fake": scores["is_fake"],
        "confidence": scores["confidence"],
        "model_fingerprint": fp,
        "artifact_signatures": artifacts,
        "frame_analysis": frame_results,
        "processing_time_ms": proc_time,
        "file_size_mb": file_size,
        "resolution": resolution,
        "metadata_anomalies": provenance["anomalies"],
        "ai_generation_indicators": provenance.get("ai_generation_indicators", []),
        "provenance_score": provenance["provenance_score"],
        "recommendation": scores["recommendation"],
    }

    result["_db_meta"] = {
        "filename": filename,
        "file_hash": file_hash,
    }

    return result


def process_audio(file_path: str, filename: str) -> dict:
    """Run full audio detection pipeline. Returns result dict."""
    t0 = time.time()

    file_hash = sha256_file(file_path)
    raw = _audio_detector.predict(file_path)
    scores = compute_final_score(raw, "audio")
    provenance = analyze_metadata(file_path, "audio")
    artifacts = build_artifact_list(raw.artifact_scores)
    fp = fingerprint_model(raw.artifact_scores)
    file_size = round(os.path.getsize(file_path) / 1024 / 1024, 3)
    proc_time = round((time.time() - t0) * 1000, 1)

    result = {
        "media_type": "audio",
        "is_fake": scores["is_fake"],
        "confidence": scores["confidence"],
        "model_fingerprint": fp,
        "artifact_signatures": artifacts,
        "frame_analysis": None,
        "processing_time_ms": proc_time,
        "file_size_mb": file_size,
        "resolution": None,
        "metadata_anomalies": provenance["anomalies"],
        "ai_generation_indicators": provenance.get("ai_generation_indicators", []),
        "provenance_score": provenance["provenance_score"],
        "recommendation": scores["recommendation"],
    }

    result["_db_meta"] = {
        "filename": filename,
        "file_hash": file_hash,
    }

    return result
