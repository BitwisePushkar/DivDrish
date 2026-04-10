"""
Authentication decorators.

Supports dual auth: JWT Bearer token OR API Key (X-API-Key header).
If neither is configured, auth is disabled (dev mode).
"""
import functools
from datetime import datetime, timezone

from flask import request, g
from jose import jwt, JWTError

from app.config.settings import get_config
from app.utils.responses import error_response
from app.utils.logger import logger


def require_auth(f):
    """
    Flask decorator that validates authentication.

    Accepts either:
      - Authorization: Bearer <jwt_token>
      - X-API-Key: <api_key>

    If no API keys are configured and no JWT secret is set,
    auth is disabled (development mode).

    Sets g.current_user with user info on success.
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        config = get_config()

        # Check if auth is disabled (dev mode)
        has_api_keys = bool(config.api_key_list)
        has_secret = config.SECRET_KEY != "change-me-in-production"

        if not has_api_keys and not has_secret:
            g.current_user = None
            return f(*args, **kwargs)

        # ─── Try JWT Bearer token first ──────────────────
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = jwt.decode(
                    token,
                    config.SECRET_KEY,
                    algorithms=["HS256"],
                )
                # Check expiration
                exp = payload.get("exp")
                if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                    return error_response("Token expired", 401)

                g.current_user = {
                    "user_id": payload.get("sub"),
                    "email": payload.get("email"),
                    "type": "jwt",
                }
                return f(*args, **kwargs)

            except JWTError as e:
                logger.warning(f"Invalid JWT: {e}")
                return error_response("Invalid or expired token", 401)

        # ─── Try API Key ────────────────────────────────
        api_key = request.headers.get("X-API-Key")

        if api_key is None:
            logger.warning("Request missing authentication")
            return error_response(
                "Authentication required. Provide Authorization: Bearer <token> or X-API-Key header.",
                401,
            )

        if has_api_keys and api_key not in config.api_key_list:
            logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
            return error_response("Invalid API key", 403)

        # Check if it's a user-specific API key
        from app.database.models import User
        user = User.query.filter_by(api_key=api_key, is_active=True).first()
        g.current_user = {
            "user_id": user.id if user else None,
            "email": user.email if user else None,
            "type": "api_key",
        }
        return f(*args, **kwargs)

    return decorated
