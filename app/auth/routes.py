"""
Authentication routes blueprint.
"""
from flask import Blueprint, request, g
from app.auth.schemas import RegisterSchema, LoginSchema, RefreshSchema, UserSchema
from app.auth.controllers import register_user, login_user, refresh_access_token, get_user_by_id
from app.auth.decorators import require_auth
from app.utils.responses import success_response, error_response
from app.utils.logger import logger

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

_register_schema = RegisterSchema()
_login_schema = LoginSchema()
_refresh_schema = RefreshSchema()
_user_schema = UserSchema()


@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user account."""
    json_data = request.get_json()
    if not json_data:
        return error_response("Request body required", 400)

    errors = _register_schema.validate(json_data)
    if errors:
        return error_response("Validation error", 422, errors)

    data = _register_schema.load(json_data)

    try:
        user = register_user(data["email"], data["password"])
        return success_response(user, 201, "User registered successfully")
    except ValueError as e:
        return error_response(str(e), 409)
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        return error_response("Registration failed", 500)


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate and receive JWT tokens."""
    json_data = request.get_json()
    if not json_data:
        return error_response("Request body required", 400)

    errors = _login_schema.validate(json_data)
    if errors:
        return error_response("Validation error", 422, errors)

    data = _login_schema.load(json_data)

    try:
        tokens = login_user(data["email"], data["password"])
        return success_response(tokens, 200, "Login successful")
    except ValueError as e:
        return error_response(str(e), 401)
    except Exception as e:
        logger.error(f"Login failed: {e}")
        return error_response("Login failed", 500)


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    """Refresh an expired access token."""
    json_data = request.get_json()
    if not json_data:
        return error_response("Request body required", 400)

    errors = _refresh_schema.validate(json_data)
    if errors:
        return error_response("Validation error", 422, errors)

    data = _refresh_schema.load(json_data)

    try:
        tokens = refresh_access_token(data["refresh_token"])
        return success_response(tokens, 200, "Token refreshed successfully")
    except ValueError as e:
        return error_response(str(e), 401)
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        return error_response("Token refresh failed", 500)


@auth_bp.route("/me", methods=["GET"])
@require_auth
def me():
    """Get current authenticated user info."""
    current_user = getattr(g, "current_user", None)
    if not current_user or not current_user.get("user_id"):
        return error_response("User not found", 404)

    user = get_user_by_id(current_user["user_id"])
    if not user:
        return error_response("User not found", 404)

    return success_response(user)
