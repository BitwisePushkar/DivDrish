from app.extensions import celery
from app.detection.controllers import process_image, process_video, process_audio
from app.utils.file_handler import cleanup
from app.utils.logger import logger
from app.database import repository

@celery.task(bind=True, name="detect_image_task", max_retries=2)
def detect_image_task(self, file_path: str, filename: str):
    try:
        result = process_image(file_path, filename)
        _save_result(result)
        cleanup(file_path) 
        return result
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            logger.error(f"Image detection task failed after max retries: {exc}")
            cleanup(file_path) 
        else:
            logger.warning(f"Retrying image detection task due to: {exc}")
            raise self.retry(exc=exc, countdown=5)
        return {"error": str(exc), "status": "failed"}

@celery.task(bind=True, name="detect_video_task", max_retries=2)
def detect_video_task(self, file_path: str, filename: str):
    try:
        result = process_video(file_path, filename)
        _save_result(result)
        cleanup(file_path)
        return result
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            logger.error(f"Video detection task failed after max retries: {exc}")
            cleanup(file_path)
        else:
            logger.warning(f"Retrying video detection task due to: {exc}")
            raise self.retry(exc=exc, countdown=10)
        return {"error": str(exc), "status": "failed"}

@celery.task(bind=True, name="detect_audio_task", max_retries=2)
def detect_audio_task(self, file_path: str, filename: str):
    try:
        result = process_audio(file_path, filename)
        _save_result(result)
        cleanup(file_path)
        return result
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            logger.error(f"Audio detection task failed after max retries: {exc}")
            cleanup(file_path)
        else:
            logger.warning(f"Retrying audio detection task due to: {exc}")
            raise self.retry(exc=exc, countdown=5)
        return {"error": str(exc), "status": "failed"}

@celery.task(name="detect_batch_task")
def detect_batch_task(items: list):
    processors = {
        "image": process_image,
        "video": process_video,
        "audio": process_audio,
    }
    results = []
    for item in items:
        file_path = item.get("file_path", "")
        try:
            processor = processors.get(item["media_type"])
            if not processor:
                results.append({
                    "filename": item["filename"],
                    "success": False,
                    "result": None,
                    "error": f"Unknown media type: {item['media_type']}",
                })
                cleanup(file_path)
                continue
            result = processor(file_path, item["filename"])
            _save_result(result)
            results.append({
                "filename": item["filename"],
                "success": True,
                "result": result,
                "error": None,
            })
            cleanup(file_path) 
        except Exception as e:
            logger.error(f"Batch item failed ({item['filename']}): {e}")
            results.append({
                "filename": item["filename"],
                "success": False,
                "result": None,
                "error": str(e),
            })
            cleanup(file_path)
    return results

def _save_result(result: dict):
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
        logger.error(f"DB save in task failed: {e}")