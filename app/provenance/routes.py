"""
Provenance analysis routes blueprint.
"""
from flask import Blueprint, request
from app.auth.decorators import require_auth
from app.provenance.controllers import analyze_provenance
from app.provenance.schemas import ProvenanceReportSchema
from app.utils.file_handler import save_upload, cleanup, detect_media_type
from app.utils.responses import success_response, error_response
from app.utils.logger import logger

provenance_bp = Blueprint("provenance", __name__, url_prefix="/provenance")

_provenance_schema = ProvenanceReportSchema()


@provenance_bp.route("/analyze", methods=["POST"])
@require_auth
def analyze():
    """
    Analyze file metadata for signs of manipulation or synthetic origin.
    Lightweight check — no ML inference.
    """
    if "file" not in request.files:
        return error_response("No file provided. Use 'file' field.", 400)

    file = request.files["file"]
    media_type = detect_media_type(file.content_type)

    if not media_type:
        return error_response(
            f"Unsupported media type: {file.content_type}", 422
        )

    from app.config.settings import get_config
    config = get_config()
    max_mb = getattr(config, f"MAX_{media_type.upper()}_MB", 200)

    try:
        path = save_upload(file, media_type, max_mb)
    except ValueError as e:
        return error_response(str(e), 422)

    try:
        result = analyze_provenance(path, file.filename or "unknown", media_type)
        return success_response(_provenance_schema.dump(result))
    except Exception as e:
        logger.error(f"Provenance analysis failed: {e}")
        return error_response(f"Analysis failed: {str(e)}", 500)
    finally:
        cleanup(path)
