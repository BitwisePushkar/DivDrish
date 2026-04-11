from app.database.repository import (
    get_analysis,
    list_analyses,
    delete_analysis,
    get_stats,
)

def get_history(page, page_size, media_type=None, is_fake=None, user_id=None):
    rows, total = list_analyses(
        page=page,
        page_size=page_size,
        media_type=media_type,
        is_fake=is_fake,
        user_id=user_id,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": rows,
    }

def get_single(record_id, user_id=None):
    return get_analysis(record_id, user_id=user_id)

def delete_single(record_id, user_id=None):
    return delete_analysis(record_id, user_id=user_id)

def get_statistics(user_id=None):
    return get_stats(user_id=user_id)