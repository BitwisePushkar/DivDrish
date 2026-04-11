import uuid
import json
import os
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
from app.tasks.email_tasks import send_otp_email_task
from app.utils.s3_service import s3_service


OTP_EXPIRY = 600       
LOCKOUT_DURATION = 3600  
MAX_ATTEMPTS = 5
THROTTLE_WINDOW = 600 
MAX_OTP_REQUESTS = 3

def register_user(username: str, email: str, password: str) -> dict:
    email = email.lower().strip()
    existing_user = User.query.filter(
        (func.lower(User.email) == func.lower(email)) | 
        (func.lower(User.username) == func.lower(username))
    ).first()
    if existing_user:
        raise ValueError("Username or email already registered")
    if _is_throttled(email, "reg_otp"):
        raise ValueError("Too many verification attempts. Please try again later.")
    otp = f"{random.randint(100000, 999999)}"
    registration_data = {
        "username": username,
        "email": email,
        "password_hash": generate_password_hash(password)
    }
    redis_client.setex(
        f"otp:reg:{email}", 
        OTP_EXPIRY, 
        json.dumps({"otp": otp, "data": registration_data})
    )
    _increment_throttle(email, "reg_otp")
    send_otp_email_task.delay(email, otp, "registration")
    return {"message": "Verification code sent to email", "email": email}

def resend_registration_otp(email: str) -> dict:
    email = email.lower().strip()
    cached = redis_client.get(f"otp:reg:{email}")
    if not cached:
        raise ValueError("No registration in progress for this email. Please register again.")
    if _is_throttled(email, "reg_otp"):
        raise ValueError("Too many resend attempts. Please try again later.")
    payload = json.loads(cached)
    new_otp = f"{random.randint(100000, 999999)}"
    payload["otp"] = new_otp
    redis_client.setex(
        f"otp:reg:{email}", 
        OTP_EXPIRY, 
        json.dumps(payload)
    )
    _increment_throttle(email, "reg_otp")
    send_otp_email_task.delay(email, new_otp, "registration")
    return {"message": "New verification code sent to email", "email": email}

def verify_registration_otp(email: str, otp: str) -> dict:
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
    redis_client.delete(f"otp:reg:{email}")
    redis_client.delete(f"attempts:{email}")
    logger.info(f"User verified and registered: {email}")
    return _generate_auth_packet(user)

def login_user(identifier: str, password: str) -> dict:
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
    email = email.lower().strip()
    user = User.query.filter(func.lower(User.email) == func.lower(email), User.is_active == True).first()
    if not user:
        return {"message": "If the account exists, a reset code has been sent."}
    if _is_throttled(email, "reset_otp"):
        raise ValueError("Too many reset attempts. Try again later.")
    otp = f"{random.randint(100000, 999999)}"
    redis_client.setex(f"otp:reset:{email}", OTP_EXPIRY, otp)
    _increment_throttle(email, "reset_otp")
    send_otp_email_task.delay(email, otp, "password_reset")
    return {"message": "Verification code sent to email", "email": email}

def verify_password_reset_otp(email: str, otp: str) -> dict:
    email = email.lower().strip()
    if _is_locked_out(email):
        raise ValueError("Account locked due to multiple failures. Try again in 1 hour.")
    cached_otp = redis_client.get(f"otp:reset:{email}")
    if not cached_otp:
        raise ValueError("Invalid or expired reset code")
    val = cached_otp.decode() if isinstance(cached_otp, bytes) else cached_otp
    if val != otp:
        _increment_failure(email)
        raise ValueError("Invalid or expired reset code")
    reset_token = str(uuid.uuid4().hex)
    redis_client.setex(f"tok:reset:{email}", 900, reset_token)
    redis_client.delete(f"otp:reset:{email}")
    redis_client.delete(f"attempts:{email}")
    return {"reset_token": reset_token, "message": "Code verified. You can now reset your password."}

def confirm_password_reset(email: str, reset_token: str, new_password: str) -> dict:
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
    config = get_config()
    try:
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
    user = db.session.get(User, user_id)
    if not user:
        raise ValueError("User not found")
    if username is not None:
        username = username.strip()
        if len(username) < 5 or len(username) > 50:
            raise ValueError("Username must be between 5 and 50 characters")
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
    user = db.session.get(User, user_id)
    if not user:
        raise ValueError("User not found")
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

def _generate_auth_packet(user: User) -> dict:
    config = get_config()
    access = _create_token(user, timedelta(hours=config.JWT_EXPIRY_HOURS), "access")
    refresh = _create_token(user, timedelta(days=config.JWT_REFRESH_EXPIRY_DAYS), "refresh")
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": config.JWT_EXPIRY_HOURS * 3600,
        "user": user.to_dict()
    }

def _create_token(user: User, expires_delta: timedelta, token_type: str) -> str:
    config = get_config()
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
        redis_client.expire(key, 1800)
    if count >= MAX_ATTEMPTS:
        redis_client.setex(f"block:{ident}", LOCKOUT_DURATION, "1")
        redis_client.delete(key)
        logger.warning(f"User {ident} locked out for 1 hour due to too many failures.")