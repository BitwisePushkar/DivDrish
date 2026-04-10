"""
WSGI entry point for Gunicorn.

Usage:
    gunicorn wsgi:app --config gunicorn.conf.py
"""
from app import create_app
from app.extensions import celery as _celery

app = create_app()

# Expose the configured celery instance for the worker (-A wsgi.celery)
celery = _celery
