"""
History routes — user-scoped analysis history and statistics.

Each authenticated user sees ONLY their own detection records.
"""
from flask import request, g
from app.auth.decorators import require_auth
from app.history.controllers import get_history, get_single, delete_single, get_statistics
from app.history.schemas import PaginatedHistorySchema, AnalysisRecordSchema, AnalysisStatsSchema
from app.auth.swagger_models import MessageResponse, ErrorResponse
from app.utils.responses import success_response, error_response
from app.utils.logger import logger

from flask_openapi3 import APIBlueprint, Tag

_tag = Tag(name="History", description="Access to past detection records and usage statistics")
_security = [{"jwt": []}]
history_bp = APIBlueprint("history", __name__, url_prefix="/history")

_paginated_schema = PaginatedHistorySchema()
_record_schema = AnalysisRecordSchema()
_stats_schema = AnalysisStatsSchema()


@history_bp.get(
    "",
    tags=[_tag],
    summary="List analysis history",
    description="Retrieve paginated analysis history (scoped to authenticated user). Supports optional filters for media type and detection result.",
    security=_security,
)
@require_auth
def list_history():
    """Retrieve paginated analysis history for the current user."""
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    media_type = request.args.get("media_type", None, type=str)
    is_fake_str = request.args.get("is_fake", None, type=str)

    # Parse boolean
    is_fake = None
    if is_fake_str is not None:
        is_fake = is_fake_str.lower() in ("true", "1", "yes")

    # Validate
    page = max(1, page)
    page_size = max(1, min(100, page_size))

    # Get current user id for scoping
    current_user = getattr(g, "current_user", None)
    user_id = current_user.get("user_id") if current_user else None

    try:
        result = get_history(page, page_size, media_type, is_fake, user_id=user_id)
        return success_response(_paginated_schema.dump(result))
    except Exception as e:
        logger.error(f"History retrieval failed: {e}")
        return error_response(f"Failed to retrieve history: {str(e)}", 500)


@history_bp.get(
    "/stats",
    tags=[_tag],
    summary="Get user analysis statistics",
    description="Aggregate statistics scoped to the authenticated user's analysis records.",
    security=_security,
)
@require_auth
def stats():
    """Aggregate statistics for the current user."""
    current_user = getattr(g, "current_user", None)
    user_id = current_user.get("user_id") if current_user else None

    try:
        result = get_statistics(user_id=user_id)
        return success_response(_stats_schema.dump(result))
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        return error_response(f"Failed to retrieve stats: {str(e)}", 500)


@history_bp.get(
    "/<record_id>",
    tags=[_tag],
    summary="Get single analysis record details",
    security=_security,
)
@require_auth
def get_record(record_id):
    """Get full details of a single analysis record (owned by current user)."""
    current_user = getattr(g, "current_user", None)
    user_id = current_user.get("user_id") if current_user else None

    record = get_single(record_id, user_id=user_id)
    if not record:
        return error_response("Record not found", 404)
    return success_response(_record_schema.dump(record))


@history_bp.delete(
    "/<record_id>",
    tags=[_tag],
    summary="Delete an analysis record",
    security=_security,
)
@require_auth
def delete_record(record_id):
    """Permanently delete an analysis record (owned by current user)."""
    current_user = getattr(g, "current_user", None)
    user_id = current_user.get("user_id") if current_user else None

    success = delete_single(record_id, user_id=user_id)
    if not success:
        return error_response("Record not found", 404)
    return success_response({"message": "Record deleted successfully", "id": record_id})
