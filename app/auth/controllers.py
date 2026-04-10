"""
Auth business logic — registration, login, token generation.
"""
import uuid
from datetime import datetime, timezone, timedelta

from jose import jwt

from app.config.settings import get_config
from app.database.models import User
from app.extensions import db
from app.utils.logger import logger


def register_user(email: str, password: str) -> dict:
    """Register a new user. Returns user dict or raises ValueError."""
    existing = User.query.filter_by(email=email).first()
    if existing:
        raise ValueError("Email already registered")

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        api_key=_generate_api_key(),
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()
    logger.info(f"User registered: {email}")

    return user.to_dict()


def login_user(email: str, password: str) -> dict:
    """Authenticate user and return tokens. Raises ValueError on failure."""
    user = User.query.filter_by(email=email, is_active=True).first()
    if not user or not user.check_password(password):
        raise ValueError("Invalid email or password")

    config = get_config()
    access_token = _create_token(
        user,
        expires_delta=timedelta(hours=config.JWT_EXPIRY_HOURS),
        token_type="access",
    )
    refresh_token = _create_token(
        user,
        expires_delta=timedelta(days=config.JWT_REFRESH_EXPIRY_DAYS),
        token_type="refresh",
    )

    logger.info(f"User logged in: {email}")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": config.JWT_EXPIRY_HOURS * 3600,
    }


def refresh_access_token(refresh_token: str) -> dict:
    """Generate new access token from refresh token. Raises ValueError on failure."""
    config = get_config()
    try:
        payload = jwt.decode(
            refresh_token,
            config.SECRET_KEY,
            algorithms=["HS256"],
        )
    except Exception:
        raise ValueError("Invalid refresh token")

    if payload.get("type") != "refresh":
        raise ValueError("Invalid token type")

    user = db.session.get(User, payload.get("sub"))
    if not user or not user.is_active:
        raise ValueError("User not found or inactive")

    access_token = _create_token(
        user,
        expires_delta=timedelta(hours=config.JWT_EXPIRY_HOURS),
        token_type="access",
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": config.JWT_EXPIRY_HOURS * 3600,
    }


def get_user_by_id(user_id: str) -> dict | None:
    """Get user dict by ID."""
    user = db.session.get(User, user_id)
    return user.to_dict() if user else None


def _create_token(user: User, expires_delta: timedelta, token_type: str) -> str:
    """Create a JWT token."""
    config = get_config()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "email": user.email,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, config.SECRET_KEY, algorithm="HS256")


def _generate_api_key() -> str:
    """Generate a random API key."""
    return f"dt_{uuid.uuid4().hex}"
