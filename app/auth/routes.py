"""
Authentication routes blueprint.
"""
from flask import Blueprint, request, g
from app.auth.schemas import (
    RegisterSchema, 
    VerifyOTPSchema, 
    LoginSchema, 
    RefreshSchema, 
    UserSchema,
    PasswordResetRequestSchema,
    PasswordResetConfirmSchema
)
from app.auth.controllers import (
    register_user, 
    verify_registration_otp,
    login_user, 
    refresh_access_token, 
    get_user_by_id,
    request_password_reset,
    verify_password_reset_otp,
    confirm_password_reset
)
from app.auth.decorators import require_auth
from app.utils.responses import success_response, error_response
from app.utils.logger import logger
from app.extensions import limiter

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# Schemas
_register_schema = RegisterSchema()
_verify_otp_schema = VerifyOTPSchema()
_login_schema = LoginSchema()
_refresh_schema = RefreshSchema()
_user_schema = UserSchema()
_reset_req_schema = PasswordResetRequestSchema()
_reset_confirm_schema = PasswordResetConfirmSchema()


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per hour")
def register():
    """Initial registration — sends OTP."""
    json_data = request.get_json()
    if not json_data:
        return error_response("Request body required", 400)

    # Validate passwords match and other fields
    errors = _register_schema.validate(json_data, context=json_data)
    if errors:
        return error_response("Validation error", 422, errors)

    data = _register_schema.load(json_data)

    try:
        result = register_user(data["username"], data["email"], data["password"])
        return success_response(result, 201)
    except ValueError as e:
        return error_response(str(e), 400) # Bad request for duplicate or throttled
    except Exception as e:
        logger.error(f"Registration initiation failed: {e}")
        return error_response("Failed to send verification code", 500)


@auth_bp.route("/verify-otp", methods=["POST"])
@limiter.limit("10 per minute")
def verify_otp():
    """Verify registration OTP and create account."""
    json_data = request.get_json()
    errors = _verify_otp_schema.validate(json_data)
    if errors:
        return error_response("Validation error", 422, errors)

    data = _verify_otp_schema.load(json_data)

    try:
        result = verify_registration_otp(data["email"], data["otp"])
        return success_response(result, 201, "Account verified successfully")
    except ValueError as e:
        return error_response(str(e), 401)
    except Exception as e:
        logger.error(f"OTP verification failed: {e}")
        return error_response("Verification failed", 500)


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    """Authenticate via email/username and receive JWT tokens."""
    json_data = request.get_json()
    errors = _login_schema.validate(json_data)
    if errors:
        return error_response("Validation error", 422, errors)

    data = _login_schema.load(json_data)

    try:
        tokens = login_user(data["identifier"], data["password"])
        return success_response(tokens, 200, "Login successful")
    except ValueError as e:
        return error_response(str(e), 401)
    except Exception as e:
        logger.error(f"Login failed: {e}")
        return error_response("Login failed", 500)


@auth_bp.route("/password-reset/request", methods=["POST"])
@limiter.limit("3 per hour")
def reset_request():
    """Request a password reset OTP."""
    json_data = request.get_json()
    errors = _reset_req_schema.validate(json_data)
    if errors:
        return error_response("Validation error", 422, errors)

    try:
        result = request_password_reset(json_data["email"])
        return success_response(result)
    except Exception as e:
        logger.error(f"Password reset request failed: {e}")
        return error_response(str(e), 500)


@auth_bp.route("/password-reset/verify", methods=["POST"])
@limiter.limit("10 per minute")
def reset_verify():
    """Verify reset OTP and get reset token."""
    json_data = request.get_json()
    # reuse VerifyOTPSchema
    errors = _verify_otp_schema.validate(json_data)
    if errors:
        return error_response("Validation error", 422, errors)

    try:
        result = verify_password_reset_otp(json_data["email"], json_data["otp"])
        return success_response(result)
    except ValueError as e:
        return error_response(str(e), 401)
    except Exception as e:
        logger.error(f"Reset verification failed: {e}")
        return error_response("Verification failed", 500)


@auth_bp.route("/password-reset/confirm", methods=["POST"])
def reset_confirm():
    """Finalize password reset."""
    json_data = request.get_json()
    errors = _reset_confirm_schema.validate(json_data)
    if errors:
        return error_response("Validation error", 422, errors)

    data = _reset_confirm_schema.load(json_data)

    try:
        result = confirm_password_reset(data["email"], data["reset_token"], data["new_password"])
        return success_response(result)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Password reset confirmation failed: {e}")
        return error_response("Failed to update password", 500)


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
