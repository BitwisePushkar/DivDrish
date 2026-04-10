"""
Community controllers.
"""
from app.community.repository import create_post, get_post, list_posts, delete_post


def add_post(user_id: str, analysis_id: str, title: str | None = None, description: str | None = None):
    """Add a new community post."""
    post = create_post(user_id, analysis_id, title, description)
    return post.to_dict()

def fetch_posts(page: int, page_size: int):
    """Fetch paginated community posts."""
    posts, total = list_posts(page, page_size)
    return {
        "items": posts,
        "total": total,
        "page": page,
        "page_size": page_size
    }

def fetch_single_post(post_id: str):
    """Fetch a single post."""
    post = get_post(post_id)
    return post.to_dict() if post else None

def remove_post(post_id: str, user_id: str):
    """Remove a post if owned by the user."""
    return delete_post(post_id, user_id)
