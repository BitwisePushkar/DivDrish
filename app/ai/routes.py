import os
import uuid
from flask import request, current_app
from werkzeug.utils import secure_filename
from app.ai import ai_bp
from app.ai.swagger_models import ChatBotRequest, DetectMediaResponse, ChatBotResponse
from app.ai.controllers import analyze_media_with_gemini, chat_with_gemini
from app.utils.logger import logger
from app.auth.decorators import require_auth
from app.extensions import limiter
from app.auth.swagger_models import ErrorResponse 

@ai_bp.post(
    "/detect",
    summary="Detect AI media using Gemini",
    description="Upload an image, video, or audio file to be analyzed by Gemini to detect if it is AI generated and where it's available online.",
    responses={
        200: DetectMediaResponse,
        400: ErrorResponse,
        500: ErrorResponse,
    }
)
@limiter.limit("10 per minute")
@require_auth
def detect_media():
    if "file" not in request.files:
        return {"status": "error", "message": "No file part in the request"}, 400
    file = request.files["file"]
    if file.filename == "":
        return {"status": "error", "message": "No selected file"}, 400
    upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
    os.makedirs(upload_folder, exist_ok=True)
    filename = secure_filename(file.filename)
    unique_id = str(uuid.uuid4())[:8]
    temp_filename = f"{unique_id}_{filename}"
    temp_path = os.path.join(upload_folder, temp_filename)
    file.save(temp_path)
    try:
        mime_type = file.mimetype
        if not mime_type or mime_type == "application/octet-stream":
            ext = filename.rsplit(".", 1)[-1].lower()
            if ext in ["mp4", "avi", "mov", "mkv"]:
                mime_type = "video/mp4"
            elif ext in ["jpg", "jpeg", "png", "webp"]:
                mime_type = "image/jpeg"
            elif ext in ["mp3", "wav", "ogg"]:
                mime_type = "audio/mpeg"
        logger.info(f"Processing Gemini detect for {temp_filename} ({mime_type})")
        result = analyze_media_with_gemini(temp_path, mime_type)
        return {
            "status": "success",
            "message": "Media analyzed successfully",
            "data": result
        }, 200    
    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
        return {"status": "error", "message": str(e)}, 500
    except Exception as e:
        logger.exception(f"Error during Gemini detect: {e}")
        return {"status": "error", "message": f"Analysis failed: {str(e)}"}, 500
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception as e:
                logger.error(f"Failed to delete local temp file {temp_path}: {e}")

@ai_bp.post(
    "/chat",
    summary="Interactive AI Safety Assistant",
    description="Chat with the DivDrish AI assistant to verify safety and get deepfake platform guidance.",
    responses={
        200: ChatBotResponse,
        400: ErrorResponse,
        500: ErrorResponse,
    }
)
@limiter.limit("30 per minute")
@require_auth
def ai_chat(body: ChatBotRequest):
    try:
        result = chat_with_gemini(body.message, body.history)
        return {
            "status": "success",
            "message": "Chat completed",
            "data": result
        }, 200
    except ValueError as e:
        logger.error(f"Configuration Error: {e}")
        return {"status": "error", "message": str(e)}, 500
    except Exception as e:
        logger.exception(f"Error during Gemini chat: {e}")
        return {"status": "error", "message": f"Chat failed: {str(e)}"}, 500