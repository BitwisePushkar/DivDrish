from flask import request, g
from app.auth.decorators import require_auth
from app.community.controllers import add_post, fetch_posts, fetch_single_post, remove_post
from app.community.schemas import PostCreateSchema
from app.community.swagger_models import CommunityPostCreate, PaginatedCommunityPosts, CommunityPostResponse, PaginationQuery, PostIdPath
from app.auth.swagger_models import MessageResponse, ErrorResponse
from app.utils.responses import success_response, error_response
from app.utils.logger import logger
from flask_openapi3 import APIBlueprint, Tag

_tag = Tag(name="Community", description="Share detection results with the community")
_security = [{"jwt": []}]
community_bp = APIBlueprint("community", __name__, url_prefix="/community")
_post_create_schema = PostCreateSchema()

@community_bp.post(
    "/posts",
    tags=[_tag],
    summary="Create a new community post",
    description="Share an analysis result with the community. Only the owner of the analysis can post it.",
    security=_security,
    responses={201: CommunityPostResponse, 400: ErrorResponse, 422: ErrorResponse}
)
@require_auth
def create_community_post(body: CommunityPostCreate):
    current_user = getattr(g, "current_user", None)
    if not current_user:
        return error_response("Authentication required", 401)
    user_id = current_user.get("user_id")
    json_data = request.get_json()
    errors = _post_create_schema.validate(json_data)
    if errors:
        return error_response("Validation error", 422, errors)
    data = _post_create_schema.load(json_data)
    try:
        post = add_post(
            user_id=user_id,
            analysis_id=data["analysis_id"],
            title=data.get("title"),
            description=data.get("description")
        )
        return success_response(post, 201)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Failed to create community post: {e}")
        return error_response("Internal server error", 500)

@community_bp.get(
    "/posts",
    tags=[_tag],
    summary="List community posts",
    description="Get recent community posts. Authentication is optional but allowed depending on access level.",
    responses={200: PaginatedCommunityPosts}
)
def list_community_posts(query: PaginationQuery):
    try:
        result = fetch_posts(page=query.page, page_size=query.page_size)
        return success_response(result)
    except Exception as e:
        logger.error(f"Failed to fetch community posts: {e}")
        return error_response("Failed to fetch posts", 500)

@community_bp.get(
    "/posts/<post_id>",
    tags=[_tag],
    summary="Get a community post",
    responses={200: CommunityPostResponse, 404: ErrorResponse}
)
def get_community_post(path: PostIdPath):
    try:
        post = fetch_single_post(path.post_id)
        if not post:
            return error_response("Post not found", 404)
        return success_response(post)
    except Exception as e:
        logger.error(f"Failed to fetch community post: {e}")
        return error_response("Failed to fetch post", 500)

@community_bp.delete(
    "/posts/<post_id>",
    tags=[_tag],
    summary="Delete a community post",
    security=_security,
    responses={200: MessageResponse, 403: ErrorResponse, 404: ErrorResponse}
)
@require_auth
def delete_community_post(path: PostIdPath):
    current_user = getattr(g, "current_user", None)
    if not current_user:
        return error_response("Authentication required", 401)
    user_id = current_user.get("user_id")
    try:
        success = remove_post(path.post_id, user_id)
        if not success:
            return error_response("Post not found or unauthorized", 404)
        return success_response({"message": "Post deleted successfully"})
    except Exception as e:
        logger.error(f"Failed to delete community post: {e}")
        return error_response("Failed to delete post", 500)