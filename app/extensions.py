from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from celery import Celery
from flask_mailman import Mail
import redis

db = SQLAlchemy()
ma = Marshmallow()
limiter = Limiter(
    key_func=get_remote_address,
)
mail = Mail()
redis_client = redis.from_url("redis://redis:6379/3", decode_responses=False)
cors = CORS()
celery = Celery(
    "deeptrace",
    include=[
        "app.tasks.email_tasks",
        "app.tasks.detection_tasks",
    ]
)

def init_celery(app):
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