"""
Flask request middleware.

Implements request ID injection, request logging, and timing
using Flask before_request / after_request hooks.
"""
import time
import uuid
from flask import request, g
from app.utils.logger import logger


def register_middleware(app):
    """Register all middleware hooks on the Flask app."""

    @app.before_request
    def before_request():
        # ─── Request ID ──────────────────────────────────
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.request_id = request_id
        g.request_id = request_id

        # ─── Timing ─────────────────────────────────────
        g.start_time = time.perf_counter()

    @app.after_request
    def after_request(response):
        # ─── Inject headers ─────────────────────────────
        request_id = getattr(g, "request_id", "-")
        response.headers["X-Request-ID"] = request_id

        # ─── Process time ───────────────────────────────
        start = getattr(g, "start_time", None)
        if start is not None:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            response.headers["X-Process-Time"] = f"{duration_ms}ms"
        else:
            duration_ms = 0

        # ─── Logging ────────────────────────────────────
        logger.info(
            f"[{request_id}] {request.method} {request.path} "
            f"→ {response.status_code} ({duration_ms}ms)"
        )

        return response
