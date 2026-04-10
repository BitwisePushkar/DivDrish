"""
Application configuration classes.

Supports Development, Production, and Testing environments.
All settings can be overridden via environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class BaseConfig:
    """Shared configuration across all environments."""

    APP_NAME = "DeepTrace ML Engine"
    VERSION = "2.0.0"

    # ─── Secret key for JWT signing ───────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
    JWT_REFRESH_EXPIRY_DAYS = int(os.getenv("JWT_REFRESH_EXPIRY_DAYS", "30"))

    # ─── API Keys (comma-separated) ─────────────────────
    API_KEYS = os.getenv("API_KEYS", "")

    @property
    def api_key_list(self):
        if not self.API_KEYS:
            return []
        return [k.strip() for k in self.API_KEYS.split(",") if k.strip()]

    # ─── Database ────────────────────────────────────────
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/deeptrace",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
    SQLALCHEMY_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))

    # ─── Celery / Redis ──────────────────────────────────
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    CELERY_TASK_SERIALIZER = "json"
    CELERY_RESULT_SERIALIZER = "json"
    CELERY_ACCEPT_CONTENT = ["json"]
    CELERY_RESULT_EXPIRES = 86400  # 24 hours

    # ─── Detection thresholds ────────────────────────────
    VIDEO_THRESHOLD = float(os.getenv("VIDEO_THRESHOLD", "0.70"))
    AUDIO_THRESHOLD = float(os.getenv("AUDIO_THRESHOLD", "0.65"))
    IMAGE_THRESHOLD = float(os.getenv("IMAGE_THRESHOLD", "0.72"))

    # ─── Model weights ───────────────────────────────────
    WEIGHTS_DIR = Path(os.getenv("WEIGHTS_DIR", str(BASE_DIR / "weights")))

    # ─── Upload limits ───────────────────────────────────
    MAX_VIDEO_MB = int(os.getenv("MAX_VIDEO_MB", "200"))
    MAX_AUDIO_MB = int(os.getenv("MAX_AUDIO_MB", "50"))
    MAX_IMAGE_MB = int(os.getenv("MAX_IMAGE_MB", "20"))
    MAX_CONTENT_LENGTH = MAX_VIDEO_MB * 1024 * 1024  # Flask global limit

    # ─── Video sampling ──────────────────────────────────
    FRAMES_PER_SECOND = int(os.getenv("FRAMES_PER_SECOND", "2"))
    MAX_FRAMES = int(os.getenv("MAX_FRAMES", "60"))

    # ─── Rate limiting ───────────────────────────────────
    RATE_LIMIT = os.getenv("RATE_LIMIT", "30/minute")
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

    # ─── Upload storage ──────────────────────────────────
    UPLOAD_FOLDER = str(BASE_DIR / "uploads")

    # ─── CORS ────────────────────────────────────────────
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3001").split(",")


class DevelopmentConfig(BaseConfig):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(BaseConfig):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_ECHO = False
    RATELIMIT_STORAGE_URI = os.getenv(
        "RATELIMIT_STORAGE_URI", "redis://localhost:6379/2"
    )


class TestingConfig(BaseConfig):
    """Testing configuration."""
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///test.db"
    CELERY_BROKER_URL = "memory://"
    CELERY_RESULT_BACKEND = "cache+memory://"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    env = os.getenv("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)()
