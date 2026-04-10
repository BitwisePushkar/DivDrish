"""
WSGI entry point for Gunicorn.

Usage:
    gunicorn wsgi:app --config gunicorn.conf.py
"""
from app import create_app

app = create_app()
