"""
File upload handling utilities for Flask.

Handles MIME validation, size limits, temp storage, and cleanup.
"""
import os
import tempfile
from pathlib import Path
from werkzeug.datastructures import FileStorage
from app.utils.logger import logger

ALLOWED = {
    "video": ["video/mp4", "video/mpeg", "video/webm", "video/quicktime"],
    "audio": ["audio/mpeg", "audio/wav", "audio/ogg", "audio/flac", "audio/mp4"],
    "image": ["image/jpeg", "image/png", "image/webp", "image/bmp"],
}

MIME_TO_MEDIA = {}
for media_type, mimes in ALLOWED.items():
    for mime in mimes:
        MIME_TO_MEDIA[mime] = media_type


def detect_media_type(content_type: str) -> str | None:
    """Map MIME type to media type string."""
    return MIME_TO_MEDIA.get(content_type)


def validate_file(file: FileStorage, media_type: str, max_mb: int) -> None:
    """
    Validate uploaded file MIME type and size.
    Raises ValueError on failure.
    """
    if not file or file.filename == "":
        raise ValueError("No file provided")

    if file.content_type not in ALLOWED.get(media_type, []):
        raise ValueError(
            f"Unsupported {media_type} format: {file.content_type}"
        )


def save_upload(file: FileStorage, media_type: str, max_mb: int) -> str:
    """
    Save an uploaded file to a temp location with streaming.

    Returns the temp file path. Caller must call cleanup() when done.
    Raises ValueError if validation fails.
    """
    validate_file(file, media_type, max_mb)

    suffix = Path(file.filename).suffix if file.filename else ""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)

    # Stream in chunks to handle large files
    chunk_size = 1024 * 1024  # 1 MB chunks
    total_bytes = 0
    max_bytes = max_mb * 1024 * 1024

    try:
        while True:
            chunk = file.stream.read(chunk_size)
            if not chunk:
                break
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                tmp.close()
                os.unlink(tmp.name)
                raise ValueError(
                    f"File too large: >{max_mb}MB limit"
                )
            tmp.write(chunk)
    except ValueError:
        raise
    except Exception as e:
        tmp.close()
        os.unlink(tmp.name)
        raise ValueError(f"Failed to save upload: {e}")

    tmp.close()
    return tmp.name


def cleanup(path: str) -> None:
    """Remove a temporary file, ignoring errors."""
    try:
        if path and os.path.exists(path):
            os.unlink(path)
    except Exception as e:
        logger.warning(f"Failed to cleanup temp file {path}: {e}")
