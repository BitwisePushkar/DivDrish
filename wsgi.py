from app import create_app
from app.extensions import celery as _celery

app = create_app()

celery = _celery