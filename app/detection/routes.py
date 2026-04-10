"""
Detection routes blueprint.

All detection endpoints are protected by @require_auth.
Heavy processing is offloaded to Celery when available.
"""
from flask import request
from app.auth.decorators import require_auth
from app.detection.controllers import process_image, process_video, process_audio
from app.detection.schemas import DetectionResultSchema, BatchResultSchema, TaskStatusSchema
from app.utils.file_handler import save_upload, cleanup, detect_media_type, ALLOWED
from app.utils.responses import success_response, error_response
from app.database import repository
from app.utils.logger import logger
from app.tasks.detection_tasks import (
    detect_image_task, 
    detect_video_task, 
    detect_audio_task, 
    detect_batch_task
)
from app.extensions import celery

from flask_openapi3 import APIBlueprint, Tag

_tag = Tag(name="Detection", description="AI-powered media analysis for deepfake detection")
detection_bp = APIBlueprint("detection", __name__)

_detection_schema = DetectionResultSchema()
_batch_schema = BatchResultSchema()
_task_status_schema = TaskStatusSchema()

MAX_BATCH_SIZE = 10


def _save_to_db(result: dict):
    """Persist detection result to database (fire and forget)."""
    db_meta = result.pop("_db_meta", {})
    try:
        repository.save_analysis(
            media_type=result["media_type"],
            filename=db_meta.get("filename", "unknown"),
            file_hash=db_meta.get("file_hash", ""),
            is_fake=result["is_fake"],
            confidence=result["confidence"],
            model_fingerprint=result.get("model_fingerprint"),
            artifact_signatures=result.get("artifact_signatures", []),
            provenance_score=result.get("provenance_score"),
            processing_time_ms=result["processing_time_ms"],
            file_size_mb=result["file_size_mb"],
            resolution=result.get("resolution"),
            recommendation=result["recommendation"],
            metadata_anomalies=result.get("metadata_anomalies", []),
        )
    except Exception as e:
        logger.error(f"Failed to save analysis to DB: {e}")


def _get_max_mb(media_type: str) -> int:
    """Get max upload size for media type from config."""
    from app.config.settings import get_config
    config = get_config()
    return getattr(config, f"MAX_{media_type.upper()}_MB", 200)


# ─── Auto-detect endpoint ────────────────────────────────

@detection_bp.route("/detect", methods=["POST"])
@require_auth
def detect_auto():
    """Auto-detect media type and route to appropriate detector."""
    if "file" not in request.files:
        return error_response("No file provided. Use 'file' field.", 400)

    file = request.files["file"]
    media_type = detect_media_type(file.content_type)

    if not media_type:
        return error_response(
            f"Unsupported media type: {file.content_type}", 422
        )

    handlers = {
        "image": _handle_image,
        "video": _handle_video,
        "audio": _handle_audio,
    }
    return handlers[media_type](file)


# ─── Image endpoint ──────────────────────────────────────

@detection_bp.route("/detect/image", methods=["POST"])
@require_auth
def detect_image():
    """Detect deepfake in uploaded image."""
    if "file" not in request.files:
        return error_response("No file provided. Use 'file' field.", 400)
    return _handle_image(request.files["file"])


def _handle_image(file):
    max_mb = _get_max_mb("image")
    try:
        path = save_upload(file, "image", max_mb)
    except ValueError as e:
        return error_response(str(e), 422)

    try:
        result = process_image(path, file.filename or "unknown")
        _save_to_db(result)
        return success_response(_detection_schema.dump(result))
    except Exception as e:
        logger.error(f"Image detection failed: {e}")
        return error_response(f"Detection failed: {str(e)}", 500)
    finally:
        cleanup(path)


# ─── Video endpoint ──────────────────────────────────────

@detection_bp.route("/detect/video", methods=["POST"])
@require_auth
def detect_video():
    """Detect deepfake in uploaded video."""
    if "file" not in request.files:
        return error_response("No file provided. Use 'file' field.", 400)
    return _handle_video(request.files["file"])


def _handle_video(file):
    max_mb = _get_max_mb("video")
    try:
        path = save_upload(file, "video", max_mb)
    except ValueError as e:
        return error_response(str(e), 422)

    try:
        result = process_video(path, file.filename or "unknown")
        _save_to_db(result)
        return success_response(_detection_schema.dump(result))
    except Exception as e:
        logger.error(f"Video detection failed: {e}")
        return error_response(f"Detection failed: {str(e)}", 500)
    finally:
        cleanup(path)


# ─── Audio endpoint ──────────────────────────────────────

@detection_bp.route("/detect/audio", methods=["POST"])
@require_auth
def detect_audio():
    """Detect deepfake in uploaded audio."""
    if "file" not in request.files:
        return error_response("No file provided. Use 'file' field.", 400)
    return _handle_audio(request.files["file"])


def _handle_audio(file):
    max_mb = _get_max_mb("audio")
    try:
        path = save_upload(file, "audio", max_mb)
    except ValueError as e:
        return error_response(str(e), 422)

    try:
        result = process_audio(path, file.filename or "unknown")
        _save_to_db(result)
        return success_response(_detection_schema.dump(result))
    except Exception as e:
        logger.error(f"Audio detection failed: {e}")
        return error_response(f"Detection failed: {str(e)}", 500)
    finally:
        cleanup(path)


# ─── Batch endpoint ──────────────────────────────────────

@detection_bp.route("/detect/batch", methods=["POST"])
@require_auth
def detect_batch():
    """Analyze up to 10 files in a single request."""
    files = request.files.getlist("files")

    if not files:
        return error_response("No files provided. Use 'files' field.", 400)

    if len(files) > MAX_BATCH_SIZE:
        return error_response(
            f"Too many files: {len(files)} > {MAX_BATCH_SIZE} max", 400
        )

    results = []
    for file in files:
        item = _process_batch_item(file)
        results.append(item)

    successful = [r for r in results if r["success"] and r["result"]]
    fake_count = sum(1 for r in successful if r["result"]["is_fake"])
    confidences = [r["result"]["confidence"] for r in successful]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

    batch_result = {
        "total_files": len(files),
        "processed": len(successful),
        "fake_count": fake_count,
        "average_confidence": round(avg_conf, 4),
        "results": results,
    }

    return success_response(_batch_schema.dump(batch_result))


def _process_batch_item(file) -> dict:
    """Process a single file from a batch."""
    try:
        media_type = detect_media_type(file.content_type)
        if not media_type:
            return {
                "filename": file.filename or "unknown",
                "success": False,
                "result": None,
                "error": f"Unsupported media type: {file.content_type}",
            }

        max_mb = _get_max_mb(media_type)
        path = save_upload(file, media_type, max_mb)

        try:
            processors = {
                "image": process_image,
                "video": process_video,
                "audio": process_audio,
            }
            result = processors[media_type](path, file.filename or "unknown")
            _save_to_db(result)

            return {
                "filename": file.filename or "unknown",
                "success": True,
                "result": _detection_schema.dump(result),
                "error": None,
            }
        finally:
            cleanup(path)

    except Exception as e:
        logger.error(f"Batch item failed ({file.filename}): {e}")
        return {
            "filename": file.filename or "unknown",
            "success": False,
            "result": None,
            "error": str(e),
        }


# ─── Async Endpoints ──────────────────────────────────────

@detection_bp.route("/detect/async/<media_type>", methods=["POST"])
@require_auth
def detect_async(media_type):
    """Submit an async detection task for image, video, or audio."""
    if media_type not in ["image", "video", "audio"]:
        return error_response(f"Invalid media type: {media_type}", 400)
        
    if "file" not in request.files:
        return error_response("No file provided. Use 'file' field.", 400)
    
    file = request.files["file"]
    max_mb = _get_max_mb(media_type)
    
    try:
        path = save_upload(file, media_type, max_mb)
    except ValueError as e:
        return error_response(str(e), 422)

    task_map = {
        "image": detect_image_task,
        "video": detect_video_task,
        "audio": detect_audio_task,
    }
    
    task = task_map[media_type]
    # Fire off task
    result = task.delay(path, file.filename or "unknown")
    
    return success_response({
        "task_id": result.id,
        "status": "PROCESSING",
        "message": f"Async {media_type} detection started"
    }, status_code=202)


@detection_bp.route("/detect/async/batch", methods=["POST"])
@require_auth
def detect_async_batch():
    """Submit an async batch detection task."""
    files = request.files.getlist("files")

    if not files:
        return error_response("No files provided. Use 'files' field.", 400)

    if len(files) > MAX_BATCH_SIZE:
        return error_response(
            f"Too many files: {len(files)} > {MAX_BATCH_SIZE} max", 400
        )

    items_to_process = []
    
    for file in files:
        mt = detect_media_type(file.content_type)
        if not mt:
            continue
            
        max_mb = _get_max_mb(mt)
        try:
            path = save_upload(file, mt, max_mb)
            items_to_process.append({
                "file_path": path,
                "filename": file.filename or "unknown",
                "media_type": mt
            })
        except ValueError:
            pass

    if not items_to_process:
        return error_response("No valid supported files could be processed.", 422)

    result = detect_batch_task.delay(items_to_process)
    
    return success_response({
        "task_id": result.id,
        "status": "PROCESSING",
        "total_files": len(items_to_process),
        "message": "Async batch detection started"
    }, status_code=202)


@detection_bp.route("/task/<task_id>", methods=["GET"])
@require_auth
def get_task_status(task_id):
    """Poll for the status of an async task."""
    task = celery.AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {
            'task_id': task_id,
            'status': 'PENDING',
            'result': None,
            'error': None
        }
    elif task.state != 'FAILURE':
        response = {
            'task_id': task_id,
            'status': task.state,
            'result': task.result, # Might need serialization if complex object
            'error': None
        }
    else:
        response = {
            'task_id': task_id,
            'status': task.state,
            'result': None,
            'error': str(task.info)
        }
        
    return success_response(_task_status_schema.dump(response))

