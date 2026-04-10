"""
History controllers.
"""
from app.database.repository import (
    get_analysis,
    list_analyses,
    delete_analysis,
    get_stats,
)


def get_history(page, page_size, media_type=None, is_fake=None):
    """Get paginated analysis history."""
    rows, total = list_analyses(
        page=page,
        page_size=page_size,
        media_type=media_type,
        is_fake=is_fake,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": rows,
    }


def get_single(record_id):
    """Get single analysis record."""
    return get_analysis(record_id)


def delete_single(record_id):
    """Delete single analysis record."""
    return delete_analysis(record_id)


def get_statistics():
    """Get aggregate statistics."""
    return get_stats()
