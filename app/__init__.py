"""
Flask Application Factory.

Creates and configures the Flask app with all extensions,
blueprints, middleware, and error handlers.
"""
import os
from flask import Flask, jsonify
from app.config.settings import get_config
<<<<<<< HEAD
from app.extensions import db, ma, limiter, cors, init_celery, mail, redis_client
=======
from app.extensions import db, ma, limiter, cors, init_celery
>>>>>>> dae06d5090fc8bfd141ef88547b668ff5eaecf28
from app.middleware.request_middleware import register_middleware
from app.utils.logger import logger


def create_app(config_override=None):
    """
    Create and configure the Flask application.

    Args:
        config_override: Optional config object to use instead of env-based config.
    """
    app = Flask(__name__)

    # ─── Load configuration ──────────────────────────────
    if config_override:
        app.config.from_object(config_override)
    else:
        config = get_config()
        app.config.from_object(config)

    # ─── Ensure directories exist ────────────────────────
    os.makedirs("logs", exist_ok=True)
    os.makedirs("weights", exist_ok=True)
    os.makedirs(app.config.get("UPLOAD_FOLDER", "uploads"), exist_ok=True)

    # ─── Initialize extensions ───────────────────────────
    db.init_app(app)
    ma.init_app(app)

    limiter.init_app(app)
    app.config.setdefault("RATELIMIT_DEFAULT", app.config.get("RATE_LIMIT", "30/minute"))

    cors.init_app(
        app,
        origins=app.config.get("CORS_ORIGINS", ["*"]),
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

<<<<<<< HEAD
    mail.init_app(app)

    # ─── Initialize Redis client ─────────────────────────
    redis_client.from_url(app.config.get("REDIS_URL", "redis://localhost:6379/3"))

=======
>>>>>>> dae06d5090fc8bfd141ef88547b668ff5eaecf28
    # ─── Initialize Celery ───────────────────────────────
    init_celery(app)

    # ─── Register middleware ─────────────────────────────
    register_middleware(app)

    # ─── Register error handlers ─────────────────────────
    _register_error_handlers(app)

    # ─── Register blueprints ─────────────────────────────
    from app.health.routes import health_bp
    from app.auth.routes import auth_bp
    from app.detection.routes import detection_bp
    from app.provenance.routes import provenance_bp
    from app.history.routes import history_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(detection_bp)
    app.register_blueprint(provenance_bp)
    app.register_blueprint(history_bp)

    # ─── Root endpoint ───────────────────────────────────
    @app.route("/", methods=["GET"])
    def root():
        return jsonify({
            "service": app.config.get("APP_NAME", "DeepTrace ML Engine"),
            "version": app.config.get("VERSION", "2.0.0"),
            "docs": "/health",
            "endpoints": {
                "health": "GET /health",
                "auth": "POST /auth/register, /auth/login, /auth/refresh",
                "detect": "POST /detect, /detect/image, /detect/video, /detect/audio, /detect/batch",
                "provenance": "POST /provenance/analyze",
                "history": "GET /history, /history/stats, /history/<id>",
            },
        })

    # ─── Create tables on startup ────────────────────────
    with app.app_context():
        try:
            db.create_all()
            logger.success("Database tables initialized")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")

    logger.info(f"DeepTrace ML Engine v{app.config.get('VERSION', '2.0.0')} started")

    return app


def _register_error_handlers(app):
    """Register global error handlers for consistent JSON responses."""

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({
            "status": "error",
            "error": "Bad Request",
            "detail": str(e.description) if hasattr(e, 'description') else str(e),
            "status_code": 400,
        }), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({
            "status": "error",
            "error": "Unauthorized",
            "detail": str(e.description) if hasattr(e, 'description') else str(e),
            "status_code": 401,
        }), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({
            "status": "error",
            "error": "Forbidden",
            "detail": str(e.description) if hasattr(e, 'description') else str(e),
            "status_code": 403,
        }), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "status": "error",
            "error": "Not Found",
            "detail": str(e.description) if hasattr(e, 'description') else str(e),
            "status_code": 404,
        }), 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({
            "status": "error",
            "error": "Payload Too Large",
            "detail": "File exceeds maximum upload size",
            "status_code": 413,
        }), 413

    @app.errorhandler(422)
    def unprocessable(e):
        return jsonify({
            "status": "error",
            "error": "Unprocessable Entity",
            "detail": str(e.description) if hasattr(e, 'description') else str(e),
            "status_code": 422,
        }), 422

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify({
            "status": "error",
            "error": "Rate Limit Exceeded",
            "detail": "Too many requests. Please slow down.",
            "status_code": 429,
        }), 429

    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Internal server error: {e}")
        return jsonify({
            "status": "error",
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred. Check logs.",
            "status_code": 500,
        }), 500
