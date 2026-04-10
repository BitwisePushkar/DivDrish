"""
Flask extension instances.

Created here (unbound) and initialized in the app factory
via init_app() to avoid circular imports.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from celery import Celery
<<<<<<< HEAD
from flask_mailman import Mail
import redis
=======
>>>>>>> dae06d5090fc8bfd141ef88547b668ff5eaecf28

# ─── SQLAlchemy ORM ──────────────────────────────────────
db = SQLAlchemy()

# ─── Marshmallow serialization / validation ──────────────
ma = Marshmallow()

# ─── Rate limiter ────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
<<<<<<< HEAD
)

# ─── Mail ────────────────────────────────────────────────
mail = Mail()

# ─── Redis (for OTPs/lockout) ────────────────────────────
redis_client = redis.Redis()

=======
    storage_uri="memory://",
)

>>>>>>> dae06d5090fc8bfd141ef88547b668ff5eaecf28
# ─── CORS ────────────────────────────────────────────────
cors = CORS()

# ─── Celery ──────────────────────────────────────────────
celery = Celery("deeptrace")


def init_celery(app):
    """Configure Celery to use Flask app context."""
    celery.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
        task_serializer=app.config.get("CELERY_TASK_SERIALIZER", "json"),
        result_serializer=app.config.get("CELERY_RESULT_SERIALIZER", "json"),
        accept_content=app.config.get("CELERY_ACCEPT_CONTENT", ["json"]),
        result_expires=app.config.get("CELERY_RESULT_EXPIRES", 86400),
        task_track_started=True,
    )

    class ContextTask(celery.Task):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
