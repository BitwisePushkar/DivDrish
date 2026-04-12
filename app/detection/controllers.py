from __future__ import annotations
import os
import time
from tempfile import NamedTemporaryFile
from typing import Any
import numpy as np
from loguru import logger
from PIL import Image
from app.models.audio_detector import AudioDetector
from app.models.image_detector import ImageDetector
from app.models.video_detector import VideoDetector
from app.services.artifact_scanner import build_artifact_list
from app.services.fingerprinter import fingerprint_model
from app.services.metadata_analyzer import analyze_metadata
from app.services.scorer import compute_final_score
from app.utils.hasher import sha256_file

FAKE_THRESHOLD: float = 0.80
UNCERTAIN_BAND: float = 0.12
MOBILE_EXIF_BONUS: float = -0.12  
MOBILE_MODEL_BONUS: float = -0.06
AI_SOFTWARE_BOOST: float = +0.08
NO_EXIF_SOFT_PENALTY: float = +0.03
WEIGHT_DETECTOR: float = 0.65
WEIGHT_PROVENANCE: float = 0.20
WEIGHT_FINGERPRINT: float = 0.15

assert abs(WEIGHT_DETECTOR + WEIGHT_PROVENANCE + WEIGHT_FINGERPRINT - 1.0) < 1e-6, \
    "Fusion weights must sum to 1.0"

_AI_SOFTWARE_KEYWORDS: tuple[str, ...] = (
    "stable diffusion",
    "midjourney",
    "dall-e",
    "firefly",
    "runway",
    "pika",
    "kling",
    "sora",
    "gen-2",
    "invideo",
    "synthesia",
)

_image_detector = ImageDetector()
_video_detector = VideoDetector()
_audio_detector = AudioDetector()

def get_detectors() -> dict[str, Any]:
    return {
        "image": _image_detector,
        "video": _video_detector,
        "audio": _audio_detector,
    }

def _preprocess_image(file_path: str) -> list[str]:
    paths: list[str] = [file_path]
    try:
        img = Image.open(file_path).convert("RGB")
        w, h = img.size
        mx, my = int(w * 0.10), int(h * 0.10)
        center = img.crop((mx, my, w - mx, h - my))
        f1 = NamedTemporaryFile(suffix=".jpg", delete=False, dir="/tmp")
        center.save(f1.name, quality=95)
        f1.close()
        paths.append(f1.name)
        half = img.resize((max(w // 2, 32), max(h // 2, 32)), Image.LANCZOS)
        f2 = NamedTemporaryFile(suffix=".jpg", delete=False, dir="/tmp")
        half.save(f2.name, quality=95)
        f2.close()
        paths.append(f2.name)
    except Exception as exc:
        logger.warning(
            "Preprocessing failed — falling back to single-pass: {}", exc
        )
    return paths

def _cleanup_temps(paths: list[str], original: str) -> None:
    for p in paths:
        if p != original:
            try:
                os.unlink(p)
            except OSError:
                pass

def _ensemble_predict_image(file_path: str) -> Any:
    crop_paths = _preprocess_image(file_path)
    results: list[Any] = []
    try:
        for path in crop_paths:
            try:
                results.append(_image_detector.predict(path))
            except Exception as exc:
                logger.warning("Ensemble crop failed ({}): {}", path, exc)
    finally:
        _cleanup_temps(crop_paths, file_path)
    if not results:
        raise RuntimeError("All ensemble inference passes failed for image")
    if len(results) == 1:
        return results[0]
    base = results[0]
    if hasattr(base, "artifact_scores") and isinstance(base.artifact_scores, dict):
        keys = base.artifact_scores.keys()
        base.artifact_scores = {
            k: float(np.mean([r.artifact_scores.get(k, 0.0) for r in results]))
            for k in keys
        }
        logger.debug(
            "Ensemble averaged {} crops, {} artifact keys", len(results), len(keys)
        )
    return base

def _mobile_calibration(provenance: dict) -> float:
    delta = 0.0
    meta: dict = provenance.get("raw_exif", {})
    if meta.get("GPSInfo"):
        delta += MOBILE_EXIF_BONUS
        logger.debug("Calibration: GPS found → delta {:.3f}", MOBILE_EXIF_BONUS)
    if meta.get("Make") and meta.get("Model"):
        delta += MOBILE_MODEL_BONUS
        logger.debug(
            "Calibration: Make/Model ({} {}) → delta {:.3f}",
            meta["Make"], meta["Model"], MOBILE_MODEL_BONUS,
        )
    software = str(meta.get("Software", "")).lower()
    if any(kw in software for kw in _AI_SOFTWARE_KEYWORDS):
        delta += AI_SOFTWARE_BOOST
        logger.warning(
            "Calibration: AI software tag detected ('{}') → delta +{:.3f}",
            meta.get("Software"), AI_SOFTWARE_BOOST,
        )
    if not meta:
        delta += NO_EXIF_SOFT_PENALTY
        logger.debug(
            "Calibration: No EXIF found (may be stripped by sharing app) "
            "→ soft penalty +{:.3f}", NO_EXIF_SOFT_PENALTY,
        )
    calibrated = float(np.clip(delta, -0.25, 0.25))
    logger.debug("Calibration total delta: {:.4f}", calibrated)
    return calibrated

def _fingerprint_to_conf(fp: dict | str | None) -> float:
    if isinstance(fp, dict):
        return float(np.clip(fp.get("confidence", 0.5), 0.0, 1.0))
    return 0.5

def _fuse_confidence(
    detector_conf: float,
    provenance_score: float,
    fingerprint_conf: float,
    calibration_delta: float,
) -> float:
    fused = (
        WEIGHT_DETECTOR    * float(np.clip(detector_conf,    0.0, 1.0))
        + WEIGHT_PROVENANCE  * float(np.clip(provenance_score,  0.0, 1.0))
        + WEIGHT_FINGERPRINT * float(np.clip(fingerprint_conf,  0.0, 1.0))
    )
    fused += calibration_delta
    return float(np.clip(fused, 0.0, 1.0))

def _make_verdict(confidence: float) -> tuple[bool, str]:
    uncertain_lower = FAKE_THRESHOLD - UNCERTAIN_BAND
    if confidence >= FAKE_THRESHOLD:
        return (
            True,
            (
                f"High likelihood of AI generation or manipulation "
                f"(confidence {confidence:.0%}). "
                "Treat this media with caution and verify from the source."
            ),
        )
    elif confidence >= uncertain_lower:
        return (
            False,
            (
                f"Borderline confidence ({confidence:.0%}) — result is uncertain. "
                "Manual review or a second opinion is recommended. "
                "Common causes: image shared via app that strips metadata, "
                "heavy compression, or unusual camera settings."
            ),
        )
    else:
        return (
            False,
            (
                f"Likely authentic (confidence {confidence:.0%}). "
                "No strong AI-generation or manipulation signals detected."
            ),
        )

def process_image(file_path: str, filename: str) -> dict:
    t0 = time.time()
    logger.info("Processing image: {}", filename)
    try:
        file_hash = sha256_file(file_path)
    except Exception as exc:
        logger.error("Hashing failed for {}: {}", filename, exc)
        file_hash = "error"
    try:
        raw = _ensemble_predict_image(file_path)
    except Exception as exc:
        logger.error("Ensemble predict failed for {}: {}", filename, exc)
        raise
    try:
        provenance = analyze_metadata(file_path, "image")
    except Exception as exc:
        logger.warning("Metadata analysis failed for {}: {}", filename, exc)
        provenance = {"anomalies": [], "ai_generation_indicators": [], "provenance_score": 0.5, "raw_exif": {}}
    cal_delta = _mobile_calibration(provenance)
    try:
        scores = compute_final_score(raw, "image")
        artifacts = build_artifact_list(raw.artifact_scores)
        fp = fingerprint_model(raw.artifact_scores)
    except Exception as exc:
        logger.error("Scoring failed for {}: {}", filename, exc)
        raise
    fp_conf = _fingerprint_to_conf(fp)
    confidence = _fuse_confidence(
        detector_conf=scores["confidence"],
        provenance_score=provenance["provenance_score"],
        fingerprint_conf=fp_conf,
        calibration_delta=cal_delta,
    )
    is_fake, recommendation = _make_verdict(confidence)
    try:
        file_size = round(os.path.getsize(file_path) / 1024 / 1024, 3)
        resolution = "{}x{}".format(
            raw.metadata.get("width", "?"), raw.metadata.get("height", "?")
        )
    except Exception:
        file_size = 0.0
        resolution = "unknown"
    proc_time = round((time.time() - t0) * 1000, 1)
    logger.info(
        "Image result — is_fake={} confidence={:.4f} time={}ms file={}",
        is_fake, confidence, proc_time, filename,
    )
    result = {
        "media_type": "image",
        "is_fake": is_fake,
        "confidence": round(confidence, 4),
        "model_fingerprint": fp,
        "artifact_signatures": artifacts,
        "frame_analysis": None,
        "processing_time_ms": proc_time,
        "file_size_mb": file_size,
        "resolution": resolution,
        "metadata_anomalies": provenance["anomalies"],
        "ai_generation_indicators": provenance.get("ai_generation_indicators", []),
        "provenance_score": round(provenance["provenance_score"], 4),
        "recommendation": recommendation,
    }
    result["_db_meta"] = {"filename": filename, "file_hash": file_hash}
    return result

def process_video(file_path: str, filename: str) -> dict:
    t0 = time.time()
    logger.info("Processing video: {}", filename)
    try:
        file_hash = sha256_file(file_path)
    except Exception as exc:
        logger.error("Hashing failed for {}: {}", filename, exc)
        file_hash = "error"
    try:
        raw = _video_detector.predict(file_path)
    except Exception as exc:
        logger.error("Video predict failed for {}: {}", filename, exc)
        raise
    try:
        provenance = analyze_metadata(file_path, "video")
    except Exception as exc:
        logger.warning("Metadata analysis failed for {}: {}", filename, exc)
        provenance = {"anomalies": [], "ai_generation_indicators": [], "provenance_score": 0.5, "raw_exif": {}}
    cal_delta = _mobile_calibration(provenance)
    try:
        scores = compute_final_score(raw, "video")
        artifacts = build_artifact_list(raw.artifact_scores)
        fp = fingerprint_model(raw.artifact_scores)
    except Exception as exc:
        logger.error("Scoring failed for {}: {}", filename, exc)
        raise
    fp_conf = _fingerprint_to_conf(fp)
    confidence = _fuse_confidence(
        detector_conf=scores["confidence"],
        provenance_score=provenance["provenance_score"],
        fingerprint_conf=fp_conf,
        calibration_delta=cal_delta,
    )
    is_fake, recommendation = _make_verdict(confidence)
    try:
        file_size = round(os.path.getsize(file_path) / 1024 / 1024, 3)
        resolution = raw.metadata.get("resolution", "unknown")
    except Exception:
        file_size = 0.0
        resolution = "unknown"
    frame_results: list[dict] = []
    try:
        frame_results = [
            {
                "frame_index": f["frame"],
                "timestamp_sec": f["ts"],
                "confidence": round(float(f["score"]), 4),
                "face_detected": bool(f["face"]),
            }
            for f in raw.metadata.get("frame_details", [])
        ]
    except Exception as exc:
        logger.warning("Frame detail parsing failed for {}: {}", filename, exc)
    proc_time = round((time.time() - t0) * 1000, 1)
    logger.info(
        "Video result — is_fake={} confidence={:.4f} frames={} time={}ms file={}",
        is_fake, confidence, len(frame_results), proc_time, filename,
    )
    result = {
        "media_type": "video",
        "is_fake": is_fake,
        "confidence": round(confidence, 4),
        "model_fingerprint": fp,
        "artifact_signatures": artifacts,
        "frame_analysis": frame_results,
        "processing_time_ms": proc_time,
        "file_size_mb": file_size,
        "resolution": resolution,
        "metadata_anomalies": provenance["anomalies"],
        "ai_generation_indicators": provenance.get("ai_generation_indicators", []),
        "provenance_score": round(provenance["provenance_score"], 4),
        "recommendation": recommendation,
    }
    result["_db_meta"] = {"filename": filename, "file_hash": file_hash}
    return result

def process_audio(file_path: str, filename: str) -> dict:
    t0 = time.time()
    logger.info("Processing audio: {}", filename)
    try:
        file_hash = sha256_file(file_path)
    except Exception as exc:
        logger.error("Hashing failed for {}: {}", filename, exc)
        file_hash = "error"
    try:
        raw = _audio_detector.predict(file_path)
    except Exception as exc:
        logger.error("Audio predict failed for {}: {}", filename, exc)
        raise
    try:
        provenance = analyze_metadata(file_path, "audio")
    except Exception as exc:
        logger.warning("Metadata analysis failed for {}: {}", filename, exc)
        provenance = {"anomalies": [], "ai_generation_indicators": [], "provenance_score": 0.5, "raw_exif": {}}
    cal_delta = 0.0
    try:
        scores = compute_final_score(raw, "audio")
        artifacts = build_artifact_list(raw.artifact_scores)
        fp = fingerprint_model(raw.artifact_scores)
    except Exception as exc:
        logger.error("Scoring failed for {}: {}", filename, exc)
        raise
    fp_conf = _fingerprint_to_conf(fp)
    confidence = _fuse_confidence(
        detector_conf=scores["confidence"],
        provenance_score=provenance["provenance_score"],
        fingerprint_conf=fp_conf,
        calibration_delta=cal_delta,
    )
    is_fake, recommendation = _make_verdict(confidence)
    try:
        file_size = round(os.path.getsize(file_path) / 1024 / 1024, 3)
    except Exception:
        file_size = 0.0
    proc_time = round((time.time() - t0) * 1000, 1)
    logger.info(
        "Audio result — is_fake={} confidence={:.4f} time={}ms file={}",
        is_fake, confidence, proc_time, filename,
    )
    result = {
        "media_type": "audio",
        "is_fake": is_fake,
        "confidence": round(confidence, 4),
        "model_fingerprint": fp,
        "artifact_signatures": artifacts,
        "frame_analysis": None,
        "processing_time_ms": proc_time,
        "file_size_mb": file_size,
        "resolution": None,
        "metadata_anomalies": provenance["anomalies"],
        "ai_generation_indicators": provenance.get("ai_generation_indicators", []),
        "provenance_score": round(provenance["provenance_score"], 4),
        "recommendation": recommendation,
    }
    result["_db_meta"] = {"filename": filename, "file_hash": file_hash}
    return result