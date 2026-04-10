"""
Authentication routes blueprint.
Uses flask-openapi3 APIBlueprint for Swagger UI documentation.
"""
from flask import request, g
from flask_openapi3 import APIBlueprint, Tag

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
from app.auth.swagger_models import (
    RegisterBody, VerifyOTPBody, LoginBody, RefreshBody,
    PasswordResetRequestBody, PasswordResetVerifyBody, PasswordResetConfirmBody,
    TokenResponse, MessageResponse, ResetTokenResponse, ErrorResponse, UserOut
)
from app.utils.responses import success_response, error_response
from app.utils.logger import logger
from app.extensions import limiter

# Security and tag definitions for Swagger UI
_auth_tag = Tag(name="Authentication", description="User registration, login, and password management")
_security = [{"BearerAuth": []}]

auth_bp = APIBlueprint("auth", __name__, url_prefix="/auth")

# Marshmallow schema instances
_register_schema = RegisterSchema()
_verify_otp_schema = VerifyOTPSchema()
_login_schema = LoginSchema()
_refresh_schema = RefreshSchema()
_user_schema = UserSchema()
_reset_req_schema = PasswordResetRequestSchema()
_reset_confirm_schema = PasswordResetConfirmSchema()


@auth_bp.post(
    "/register",
    summary="Register (Step 1 — send OTP)",
    description="Initiates registration. Sends a 6-digit OTP to the email provided. OTP expires in 10 minutes. Limited to 5 requests per hour.",
    tags=[_auth_tag],
    responses={
        201: MessageResponse,
        400: ErrorResponse,
        422: ErrorResponse,
        429: ErrorResponse,
    }
)
@limiter.limit("5 per hour")
def register(body: RegisterBody):
    """Initial registration — sends OTP."""
    json_data = request.get_json()
    if not json_data:
        return error_response("Request body required", 400)

    errors = _register_schema.validate(json_data)
    if errors:
        return error_response("Validation error", 422, errors)

    data = _register_schema.load(json_data)

    try:
        result = register_user(data["username"], data["email"], data["password"])
        return success_response(result, 201)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Registration initiation failed: {e}")
        return error_response("Failed to send verification code", 500)


@auth_bp.post(
    "/verify-otp",
    summary="Register (Step 2 — verify OTP)",
    description="Verifies the 6-digit OTP. On success, creates the user account and returns access + refresh tokens. 5 failed attempts trigger a 1-hour lockout.",
    tags=[_auth_tag],
    responses={
        201: TokenResponse,
        400: ErrorResponse,
        401: ErrorResponse,
        429: ErrorResponse,
    }
)
@limiter.limit("10 per minute")
def verify_otp(body: VerifyOTPBody):
    """Verify registration OTP and create account."""
    json_data = request.get_json()
    if not json_data:
        return error_response("Request body required", 400)
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


@auth_bp.post(
    "/login",
    summary="Login",
    description="Authenticates a user using either their email or username plus password. Returns access and refresh tokens.",
    tags=[_auth_tag],
    responses={
        200: TokenResponse,
        400: ErrorResponse,
        401: ErrorResponse,
    }
)
@limiter.limit("10 per minute")
def login(body: LoginBody):
    """Authenticate via email/username and receive JWT tokens."""
    json_data = request.get_json()
    if not json_data:
        return error_response("Request body required", 400)

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


@auth_bp.post(
    "/password-reset/request",
    summary="Password Reset (Step 1 — request OTP)",
    description="Sends a password reset OTP to the provided email. Silently succeeds even if email is not registered (prevents enumeration).",
    tags=[_auth_tag],
    responses={
        200: MessageResponse,
        400: ErrorResponse,
        429: ErrorResponse,
    }
)
@limiter.limit("3 per hour")
def reset_request(body: PasswordResetRequestBody):
    """Request a password reset OTP."""
    json_data = request.get_json()
    if not json_data:
        return error_response("Request body required", 400)
    errors = _reset_req_schema.validate(json_data)
    if errors:
        return error_response("Validation error", 422, errors)

    try:
        result = request_password_reset(json_data["email"])
        return success_response(result)
    except ValueError as e:
        return error_response(str(e), 429)
    except Exception as e:
        logger.error(f"Password reset request failed: {e}")
        return error_response("Failed to send reset code", 500)


@auth_bp.post(
    "/password-reset/verify",
    summary="Password Reset (Step 2 — verify OTP)",
    description="Verifies the reset OTP. On success, returns a short-lived `reset_token` valid for 15 minutes.",
    tags=[_auth_tag],
    responses={
        200: ResetTokenResponse,
        400: ErrorResponse,
        401: ErrorResponse,
    }
)
@limiter.limit("10 per minute")
def reset_verify(body: PasswordResetVerifyBody):
    """Verify reset OTP and get reset token."""
    json_data = request.get_json()
    if not json_data:
        return error_response("Request body required", 400)
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


@auth_bp.post(
    "/password-reset/confirm",
    summary="Password Reset (Step 3 — set new password)",
    description="Finalizes the password reset using the `reset_token` received in Step 2. The token is single-use and expires in 15 minutes.",
    tags=[_auth_tag],
    responses={
        200: MessageResponse,
        400: ErrorResponse,
    }
)
def reset_confirm(body: PasswordResetConfirmBody):
    """Finalize password reset."""
    json_data = request.get_json()
    if not json_data:
        return error_response("Request body required", 400)
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


@auth_bp.post(
    "/refresh",
    summary="Refresh Access Token",
    description="Issues a new short-lived access token using a valid refresh token.",
    tags=[_auth_tag],
    responses={
        200: TokenResponse,
        400: ErrorResponse,
        401: ErrorResponse,
    }
)
def refresh(body: RefreshBody):
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


@auth_bp.get(
    "/me",
    summary="Get Current User",
    description="Returns the authenticated user's profile. Requires a valid Bearer token.",
    tags=[_auth_tag],
    security=_security,
    responses={
        200: UserOut,
        401: ErrorResponse,
        404: ErrorResponse,
    }
)
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
