from flask import request
from app.auth.decorators import require_auth
from app.history.controllers import get_history, get_single, delete_single, get_statistics
from app.history.schemas import PaginatedHistorySchema, AnalysisRecordSchema, AnalysisStatsSchema
from app.utils.responses import success_response, error_response
from app.utils.logger import logger

from flask_openapi3 import APIBlueprint, Tag

_tag = Tag(name="History", description="Access to past detection records and usage statistics")
history_bp = APIBlueprint("history", __name__, url_prefix="/history")

_paginated_schema = PaginatedHistorySchema()
_record_schema = AnalysisRecordSchema()
_stats_schema = AnalysisStatsSchema()


@history_bp.route("", methods=["GET"])
@require_auth
def list_history():
    """Retrieve paginated analysis history with optional filters."""
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

    try:
        result = get_history(page, page_size, media_type, is_fake)
        return success_response(_paginated_schema.dump(result))
    except Exception as e:
        logger.error(f"History retrieval failed: {e}")
        return error_response(f"Failed to retrieve history: {str(e)}", 500)


@history_bp.route("/stats", methods=["GET"])
@require_auth
def stats():
    """Aggregate statistics across all analysis records."""
    try:
        result = get_statistics()
        return success_response(_stats_schema.dump(result))
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        return error_response(f"Failed to retrieve stats: {str(e)}", 500)


@history_bp.route("/<record_id>", methods=["GET"])
@require_auth
def get_record(record_id):
    """Get full details of a single analysis record."""
    record = get_single(record_id)
    if not record:
        return error_response(f"Analysis record not found: {record_id}", 404)
    return success_response(_record_schema.dump(record))


@history_bp.route("/<record_id>", methods=["DELETE"])
@require_auth
def delete_record(record_id):
    """Delete a single analysis record."""
    deleted = delete_single(record_id)
    if not deleted:
        return error_response(f"Analysis record not found: {record_id}", 404)
    return success_response({"message": "Record deleted", "id": record_id})
