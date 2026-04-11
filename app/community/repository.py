from sqlalchemy import desc
from app.extensions import db
from app.database.models import CommunityPost, AnalysisResult
from app.utils.logger import logger

def create_post(user_id: str, analysis_id: str, title: str | None = None, description: str | None = None) -> CommunityPost | None:
    analysis = db.session.get(AnalysisResult, analysis_id)
    if not analysis or analysis.user_id != user_id:
        raise ValueError("Analysis not found or does not belong to the user")
    existing = CommunityPost.query.filter_by(analysis_id=analysis_id).first()
    if existing:
        raise ValueError("Analysis already posted to the community")
    post = CommunityPost(
        user_id=user_id,
        analysis_id=analysis_id,
        title=title,
        description=description,
    )
    try:
        db.session.add(post)
        db.session.commit()
        logger.info(f"Community post created: {post.id}")
        return post
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create community post: {e}")
        raise

def get_post(post_id: str) -> CommunityPost | None:
    return db.session.get(CommunityPost, post_id)

def list_posts(page: int = 1, page_size: int = 20) -> tuple[list[dict], int]:
    query = CommunityPost.query
    total = query.count()
    posts = (
        query
        .order_by(desc(CommunityPost.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [p.to_dict() for p in posts], total

def delete_post(post_id: str, user_id: str) -> bool:
    post = db.session.get(CommunityPost, post_id)
    if not post or post.user_id != user_id:
        return False
    try:
        db.session.delete(post)
        db.session.commit()
        logger.info(f"Community post deleted: {post_id}")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to delete community post {post_id}: {e}")
        return False