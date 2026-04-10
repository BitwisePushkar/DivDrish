"""
Auth business logic — registration, login, token generation, and security.
"""
import uuid
import json
import random
from datetime import datetime, timezone, timedelta

from jose import jwt
from werkzeug.security import generate_password_hash

from app.config.settings import get_config
from app.database.models import User
from sqlalchemy import func
from app.extensions import db, redis_client
from app.utils.logger import logger
from app.utils.email_service import send_otp_email

# ─── Config Constants ─────────────────────────────────────
OTP_EXPIRY = 600        # 10 minutes
LOCKOUT_DURATION = 3600  # 1 hour
MAX_ATTEMPTS = 5
THROTTLE_WINDOW = 600   # 10 minutes
MAX_OTP_REQUESTS = 3


def register_user(username: str, email: str, password: str) -> dict:
    """
    Initiate user registration.
    Validates input and sends an OTP. Data is cached in Redis.
    """
    email = email.lower().strip()
    
    # 1. Check if user already exists in DB (Case-Insensitive)
    existing_user = User.query.filter(
        (func.lower(User.email) == func.lower(email)) | 
        (func.lower(User.username) == func.lower(username))
    ).first()
    if existing_user:
        raise ValueError("Username or email already registered")

    # 2. Check throttling for OTP requests
    if _is_throttled(email, "reg_otp"):
        raise ValueError("Too many verification attempts. Please try again later.")

    # 3. Generate OTP and cache data
    otp = f"{random.randint(100000, 999999)}"
    registration_data = {
        "username": username,
        "email": email,
        "password_hash": generate_password_hash(password)
    }
    
    # Store registration data with OTP in Redis
    redis_client.setex(
        f"otp:reg:{email}", 
        OTP_EXPIRY, 
        json.dumps({"otp": otp, "data": registration_data})
    )
    
    # Increment throttle counter BEFORE sending email
    _increment_throttle(email, "reg_otp")

    # 4. Send Email (Asynchronous)
    from app.tasks.email_tasks import send_otp_email_task
    send_otp_email_task.delay(email, otp, "registration")
    
    return {"message": "Verification code sent to email", "email": email}


def resend_registration_otp(email: str) -> dict:
    """
    Resend registration OTP for an in-progress registration.
    Regenerates a new code and resets the expiry timer.
    """
    email = email.lower().strip()
    
    # 1. Check if reg data exists in Redis
    cached = redis_client.get(f"otp:reg:{email}")
    if not cached:
        raise ValueError("No registration in progress for this email. Please register again.")

    # 2. Check throttling
    if _is_throttled(email, "reg_otp"):
        raise ValueError("Too many resend attempts. Please try again later.")

    # 3. Regenerate OTP and update cache
    payload = json.loads(cached)
    new_otp = f"{random.randint(100000, 999999)}"
    payload["otp"] = new_otp
    
    redis_client.setex(
        f"otp:reg:{email}", 
        OTP_EXPIRY, 
        json.dumps(payload)
    )
    
    _increment_throttle(email, "reg_otp")

    # 4. Send Email (Asynchronous)
    from app.tasks.email_tasks import send_otp_email_task
    send_otp_email_task.delay(email, new_otp, "registration")
    
    return {"message": "New verification code sent to email", "email": email}


def verify_registration_otp(email: str, otp: str) -> dict:
    """
    Verify registration OTP and create user in DB.
    """
    email = email.lower().strip()
    
    if _is_locked_out(email):
        raise ValueError("Too many failed attempts. Try again in 1 hour.")

    cached = redis_client.get(f"otp:reg:{email}")
    if not cached:
        raise ValueError("Verification code expired or invalid")

    payload = json.loads(cached)
    if payload["otp"] != otp:
        _increment_failure(email)
        raise ValueError("Invalid verification code")

    # Success: Create User
    data = payload["data"]
    user = User(
        id=str(uuid.uuid4()),
        username=data["username"],
        email=data["email"],
        password_hash=data["password_hash"],
        api_key=_generate_api_key(),
    )
    
    db.session.add(user)
    db.session.commit()
    
    # Cleanup Redis
    redis_client.delete(f"otp:reg:{email}")
    redis_client.delete(f"attempts:{email}")
    
    logger.info(f"User verified and registered: {email}")
    return _generate_auth_packet(user)


def login_user(identifier: str, password: str) -> dict:
    """
    Authenticate user via email or username.
    """
    user = User.query.filter(
        ((func.lower(User.email) == func.lower(identifier)) | 
         (func.lower(User.username) == func.lower(identifier))) & 
        (User.is_active == True)
    ).first()
    
    if not user or not user.check_password(password):
        raise ValueError("Invalid credentials")

    logger.info(f"User logged in: {user.id}")
    return _generate_auth_packet(user)


def request_password_reset(email: str) -> dict:
    """
    Send a password reset OTP.
    """
    email = email.lower().strip()
    user = User.query.filter(func.lower(User.email) == func.lower(email), User.is_active == True).first()
    if not user:
        # Silent return to prevent email enumeration
        return {"message": "If the account exists, a reset code has been sent."}

    if _is_throttled(email, "reset_otp"):
        raise ValueError("Too many reset attempts. Try again later.")

    otp = f"{random.randint(100000, 999999)}"
    redis_client.setex(f"otp:reset:{email}", OTP_EXPIRY, otp)

    # Increment throttle counter
    _increment_throttle(email, "reset_otp")

    # Send Email (Asynchronous) - FIXED purpose to password_reset
    from app.tasks.email_tasks import send_otp_email_task
    send_otp_email_task.delay(email, otp, "password_reset")
    
    return {"message": "Verification code sent to email", "email": email}


def verify_password_reset_otp(email: str, otp: str) -> dict:
    """
    Verify reset OTP and return a temporary reset token.
    """
    email = email.lower().strip()
    
    if _is_locked_out(email):
        raise ValueError("Account locked due to multiple failures. Try again in 1 hour.")

    cached_otp = redis_client.get(f"otp:reset:{email}")
    if not cached_otp:
        raise ValueError("Invalid or expired reset code")
    
    # Handle possible bytes/string from Redis
    val = cached_otp.decode() if isinstance(cached_otp, bytes) else cached_otp
    if val != otp:
        _increment_failure(email)
        raise ValueError("Invalid or expired reset code")

    # Generate temporary reset token
    reset_token = str(uuid.uuid4().hex)
    redis_client.setex(f"tok:reset:{email}", 900, reset_token) # 15 min expiry
    redis_client.delete(f"otp:reset:{email}")
    redis_client.delete(f"attempts:{email}")

    return {"reset_token": reset_token, "message": "Code verified. You can now reset your password."}


def confirm_password_reset(email: str, reset_token: str, new_password: str) -> dict:
    """
    Finalize password reset using the temporary token.
    """
    email = email.lower().strip()
    cached_token = redis_client.get(f"tok:reset:{email}")
    
    val = cached_token.decode() if isinstance(cached_token, bytes) else cached_token
    if not val or val != reset_token:
        raise ValueError("Invalid or expired reset token")

    user = User.query.filter_by(email=email).first()
    if not user:
        raise ValueError("User not found")

    user.set_password(new_password)
    db.session.commit()
    
    redis_client.delete(f"tok:reset:{email}")
    logger.info(f"Password reset success for {email}")
    
    return {"message": "Password updated successfully"}


def refresh_access_token(refresh_token: str) -> dict:
    """Generate new access token from refresh token."""
    config = get_config()
    try:
        from jose import jwt
        payload = jwt.decode(refresh_token, config.SECRET_KEY, algorithms=["HS256"])
    except Exception:
        raise ValueError("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise ValueError("Invalid token type")

    user = db.session.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise ValueError("User not found or inactive")

    new_access = _create_token(
        user, 
        expires_delta=timedelta(hours=config.JWT_EXPIRY_HOURS), 
        token_type="access"
    )

    return {
        "access_token": new_access,
        "token_type": "bearer",
        "expires_in": config.JWT_EXPIRY_HOURS * 3600
    }


def get_user_by_id(user_id: str) -> dict | None:
    user = db.session.get(User, user_id)
    return user.to_dict() if user else None


def update_user_profile(user_id: str, display_name: str | None = None, username: str | None = None) -> dict:
    """
    Update user profile fields (display_name, username).
    Raises ValueError on validation or uniqueness failures.
    """
    user = db.session.get(User, user_id)
    if not user:
        raise ValueError("User not found")

    if username is not None:
        username = username.strip()
        if len(username) < 5 or len(username) > 50:
            raise ValueError("Username must be between 5 and 50 characters")
        # Check uniqueness (case-insensitive)
        existing = User.query.filter(
            func.lower(User.username) == func.lower(username),
            User.id != user_id
        ).first()
        if existing:
            raise ValueError("Username already taken")
        user.username = username

    if display_name is not None:
        display_name = display_name.strip()
        if len(display_name) > 100:
            raise ValueError("Display name must be 100 characters or less")
        user.display_name = display_name

    try:
        db.session.commit()
        logger.info(f"Profile updated for user {user_id}")
        return user.to_dict()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Profile update failed: {e}")
        raise ValueError("Failed to update profile")


def update_user_avatar(user_id: str, temp_path: str, original_filename: str) -> dict:
    """
    Upload a profile image to S3 and update the user's profile_image_url.
    """
    from app.utils.s3_service import s3_service

    user = db.session.get(User, user_id)
    if not user:
        raise ValueError("User not found")

    # Build S3 object key: avatars/{user_id}/{filename}
    import os
    ext = os.path.splitext(original_filename)[1] or ".jpg"
    object_name = f"avatars/{user_id}/profile{ext}"

    media_url = s3_service.upload_file(temp_path, object_name)
    if not media_url:
        raise ValueError("Failed to upload avatar image. Check S3 configuration.")

    user.profile_image_url = media_url

    try:
        db.session.commit()
        logger.info(f"Avatar updated for user {user_id}: {media_url}")
        return user.to_dict()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Avatar update failed: {e}")
        raise ValueError("Failed to save avatar URL")


# ─── Internal Helpers ─────────────────────────────────────

def _generate_auth_packet(user: User) -> dict:
    config = get_config()
    access = _create_token(user, timedelta(hours=config.JWT_EXPIRY_HOURS), "access")
    refresh = _create_token(user, timedelta(days=config.JWT_REFRESH_EXPIRY_DAYS), "refresh")
    # include_secrets=False by default (hides API Key)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": config.JWT_EXPIRY_HOURS * 3600,
        "user": user.to_dict()
    }


def _create_token(user: User, expires_delta: timedelta, token_type: str) -> str:
    config = get_config()
    from jose import jwt
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "email": user.email,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, config.SECRET_KEY, algorithm="HS256")


def _generate_api_key() -> str:
    return f"dt_{uuid.uuid4().hex}"


# ─── Security Helpers ─────────────────────────────────────

def _is_throttled(identifier: str, key_type: str) -> bool:
    key = f"throttle:{key_type}:{identifier.lower()}"
    count = redis_client.get(key)
    return count is not None and int(count) >= MAX_OTP_REQUESTS


def _increment_throttle(identifier: str, key_type: str):
    key = f"throttle:{key_type}:{identifier.lower()}"
    current = redis_client.incr(key)
    if current == 1:
        redis_client.expire(key, THROTTLE_WINDOW)


def _is_locked_out(identifier: str) -> bool:
    return redis_client.exists(f"block:{identifier.lower()}")


def _increment_failure(identifier: str):
    ident = identifier.lower()
    key = f"attempts:{ident}"
    count = redis_client.incr(key)
    if count == 1:
        redis_client.expire(key, 1800) # 30 min window for attempts
    if count >= MAX_ATTEMPTS:
        redis_client.setex(f"block:{ident}", LOCKOUT_DURATION, "1")
        redis_client.delete(key)
        logger.warning(f"User {ident} locked out for 1 hour due to too many failures.")
