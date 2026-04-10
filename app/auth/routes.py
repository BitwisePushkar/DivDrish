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
    PasswordResetConfirmSchema,
    ResendOTPSchema
)
from app.auth.controllers import (
    register_user,
    verify_registration_otp,
    login_user,
    refresh_access_token,
    get_user_by_id,
    request_password_reset,
    verify_password_reset_otp,
    confirm_password_reset,
    resend_registration_otp,
    update_user_profile,
    update_user_avatar,
)
from app.auth.decorators import require_auth
from app.auth.swagger_models import (
    RegisterBody, VerifyOTPBody, LoginBody, RefreshBody,
    PasswordResetRequestBody, PasswordResetVerifyBody, PasswordResetConfirmBody,
    ResendOTPBody, ProfileUpdateBody,
    TokenResponse, MessageResponse, ResetTokenResponse, ErrorResponse, UserOut
)
from app.utils.responses import success_response, error_response
from app.utils.logger import logger
from app.extensions import limiter

# Security and tag definitions for Swagger UI
_auth_tag = Tag(name="Authentication", description="User registration, login, and password management")
_security = [{"jwt": []}]

auth_bp = APIBlueprint("auth", __name__, url_prefix="/auth")

# Marshmallow schema instances
_register_schema = RegisterSchema()
_verify_otp_schema = VerifyOTPSchema()
_login_schema = LoginSchema()
_refresh_schema = RefreshSchema()
_user_schema = UserSchema()
_reset_req_schema = PasswordResetRequestSchema()
_reset_confirm_schema = PasswordResetConfirmSchema()
_resend_otp_schema = ResendOTPSchema()


@auth_bp.post(
    "/register",
    summary="Register (Step 1 — send OTP)",
    description="Initiates registration. Sends a 6-digit OTP to the email provided.",
    tags=[_auth_tag],
    responses={
        201: MessageResponse,
        400: ErrorResponse,
        422: ErrorResponse,
        429: ErrorResponse,
    }
)
@limiter.limit("30 per minute")
def register(body: RegisterBody):
    """Initial registration — sends OTP."""
    json_data = request.get_json()
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
    description="Verifies the 6-digit OTP and creates the user account.",
    tags=[_auth_tag],
    responses={
        201: TokenResponse,
        400: ErrorResponse,
        401: ErrorResponse,
        429: ErrorResponse,
    }
)
@limiter.limit("60 per minute")
def verify_otp(body: VerifyOTPBody):
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


@auth_bp.post(
    "/resend-otp",
    summary="Resend registration OTP",
    description="Sends a fresh verification code to the email address if registration is still in progress.",
    tags=[_auth_tag],
    responses={
        200: MessageResponse,
        400: ErrorResponse,
        404: ErrorResponse,
        429: ErrorResponse,
    }
)
@limiter.limit("20 per minute")
def resend_otp(body: ResendOTPBody):
    """Resend registration OTP."""
    json_data = request.get_json()
    errors = _resend_otp_schema.validate(json_data)
    if errors:
        return error_response("Validation error", 422, errors)

    try:
        result = resend_registration_otp(json_data["email"])
        return success_response(result)
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"OTP resend failed: {e}")
        return error_response("Failed to resend code", 500)


@auth_bp.post(
    "/login",
    summary="Login",
    description="Authenticates a user and returns tokens.",
    tags=[_auth_tag],
    responses={
        200: TokenResponse,
        400: ErrorResponse,
        401: ErrorResponse,
        429: ErrorResponse,
    }
)
@limiter.limit("60 per minute")
def login(body: LoginBody):
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


@auth_bp.post(
    "/password-reset/request",
    summary="Password Reset (Step 1 — request OTP)",
    description="Sends a password reset OTP to the provided email.",
    tags=[_auth_tag],
    responses={
        200: MessageResponse,
        400: ErrorResponse,
        429: ErrorResponse,
    }
)
@limiter.limit("20 per hour")
def reset_request(body: PasswordResetRequestBody):
    """Request a password reset OTP."""
    json_data = request.get_json()
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
    description="Verifies the reset OTP.",
    tags=[_auth_tag],
    responses={
        200: ResetTokenResponse,
        400: ErrorResponse,
        401: ErrorResponse,
        429: ErrorResponse,
    }
)
@limiter.limit("30 per minute")
def reset_verify(body: PasswordResetVerifyBody):
    """Verify reset OTP and get reset token."""
    json_data = request.get_json()
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
    description="Finalizes the password reset.",
    tags=[_auth_tag],
    responses={
        200: MessageResponse,
        400: ErrorResponse,
        401: ErrorResponse,
        429: ErrorResponse,
    }
)
def reset_confirm(body: PasswordResetConfirmBody):
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


@auth_bp.post(
    "/refresh",
    summary="Refresh Access Token",
    description="Issues a new short-lived access token.",
    tags=[_auth_tag],
    responses={
        200: TokenResponse,
        400: ErrorResponse,
        401: ErrorResponse,
        429: ErrorResponse,
    }
)
def refresh(body: RefreshBody):
    """Refresh an expired access token."""
    json_data = request.get_json()
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
    description="Returns the authenticated user's profile.",
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


@auth_bp.put(
    "/profile",
    summary="Update Profile",
    description="Update the authenticated user's display name or username.",
    tags=[_auth_tag],
    security=_security,
    responses={
        200: UserOut,
        400: ErrorResponse,
        401: ErrorResponse,
    }
)
@require_auth
def update_profile(body: ProfileUpdateBody):
    """Update user profile (display_name, username)."""
    current_user = getattr(g, "current_user", None)
    if not current_user or not current_user.get("user_id"):
        return error_response("Authentication required", 401)

    json_data = request.get_json()
    if not json_data:
        return error_response("No data provided", 400)

    try:
        updated = update_user_profile(
            user_id=current_user["user_id"],
            display_name=json_data.get("display_name"),
            username=json_data.get("username"),
        )
        return success_response(updated, message="Profile updated successfully")
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Profile update failed: {e}")
        return error_response("Failed to update profile", 500)


@auth_bp.post(
    "/profile/avatar",
    summary="Upload Profile Image",
    description="Upload or replace the authenticated user's profile avatar. Accepts image/jpeg, image/png, image/webp. Max 5MB.",
    tags=[_auth_tag],
    security=_security,
    responses={
        200: UserOut,
        400: ErrorResponse,
        401: ErrorResponse,
        422: ErrorResponse,
    }
)
@require_auth
def upload_avatar():
    """Upload a profile avatar image to S3."""
    current_user = getattr(g, "current_user", None)
    if not current_user or not current_user.get("user_id"):
        return error_response("Authentication required", 401)

    if "file" not in request.files:
        return error_response("No file provided. Use 'file' field.", 400)

    file = request.files["file"]
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        return error_response(
            f"Unsupported image type: {file.content_type}. Allowed: {', '.join(allowed_types)}",
            422
        )

    from app.utils.file_handler import save_upload, cleanup
    try:
        temp_path = save_upload(file, "image", max_mb=5)
    except ValueError as e:
        return error_response(str(e), 422)

    try:
        updated = update_user_avatar(
            user_id=current_user["user_id"],
            temp_path=temp_path,
            original_filename=file.filename or "avatar.jpg",
        )
        return success_response(updated, message="Avatar updated successfully")
    except ValueError as e:
        return error_response(str(e), 400)
    except Exception as e:
        logger.error(f"Avatar upload failed: {e}")
        return error_response("Failed to upload avatar", 500)
    finally:
        cleanup(temp_path)