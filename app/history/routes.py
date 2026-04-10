from flask import request
from app.auth.decorators import require_auth
from app.history.controllers import get_history, get_single, delete_single, get_statistics
from app.history.schemas import PaginatedHistorySchema, AnalysisRecordSchema, AnalysisStatsSchema
from app.history.swagger_models import HistoryQuery, PaginatedHistory, HistoryRecord, AnalysisStats
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
    description="Retrieve paginated analysis history with optional filters for media type and result.",
    security=_security,
    query=HistoryQuery,
    responses={200: PaginatedHistory, 401: ErrorResponse}
)
@require_auth
def list_history(query: HistoryQuery):
    """Retrieve paginated analysis history."""
    page = query.page
    page_size = query.page_size
    media_type = query.media_type
    is_fake_str = query.is_fake

    # Parse boolean
    is_fake = None
    if is_fake_str is not None:
        is_fake = is_fake_str.lower() in ("true", "1", "yes")

    # Validate
    page = max(1, page)
    page_size = max(1, min(100, page_size))

    try:
        result = get_history(page, page_size, media_type, is_fake)
        return success_response(_paginated_schema.dump(result))
    except Exception as e:
        logger.error(f"History retrieval failed: {e}")
        return error_response(f"Failed to retrieve history: {str(e)}", 500)


@history_bp.get(
    "/stats",
    tags=[_tag],
    summary="Get overall analysis statistics",
    description="Aggregate statistics across all analysis records including detection counts and confidence trends.",
    security=_security,
    responses={200: AnalysisStats, 401: ErrorResponse}
)
@require_auth
def stats():
    """Aggregate statistics."""
    try:
        result = get_statistics()
        return success_response(_stats_schema.dump(result))
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        return error_response(f"Failed to retrieve stats: {str(e)}", 500)


@history_bp.get(
    "/<record_id>",
    tags=[_tag],
    summary="Get single analysis record details",
    security=_security,
    responses={200: HistoryRecord, 401: ErrorResponse, 404: ErrorResponse}
)
@require_auth
def get_record(path_body: dict):
    """Get full details of a single analysis record."""
    record_id = path_body["record_id"]
    record = get_single(record_id)
    if not record:
        return error_response("Record not found", 404)
    return success_response(_record_schema.dump(record))


@history_bp.delete(
    "/<record_id>",
    tags=[_tag],
    summary="Delete an analysis record",
    security=_security,
    responses={200: MessageResponse, 401: ErrorResponse, 404: ErrorResponse}
)
@require_auth
def delete_record(path_body: dict):
    """Permanently delete an analysis record."""
    record_id = path_body["record_id"]
    success = delete_single(record_id)
    if not success:
        return error_response("Record not found", 404)
    return success_response({"message": "Record deleted successfully", "id": record_id})
