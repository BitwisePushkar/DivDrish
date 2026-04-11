import os
from flask import jsonify
from flask_openapi3 import OpenAPI, Info, SecurityScheme
from app.config.settings import get_config
from app.extensions import db, ma, limiter, cors, init_celery, mail, redis_client
from app.middleware.request_middleware import register_middleware
from app.utils.logger import logger
import redis as _redis
from app.health.routes import health_bp
from app.auth.routes import auth_bp
from app.detection.routes import detection_bp
from app.provenance.routes import provenance_bp
from app.history.routes import history_bp
from app.community.routes import community_bp
from app.ai.routes import ai_bp
import time

_info = Info(
    title="DivDrish — DeepTrace ML Engine",
    version="2.0.0",
    description=(
        "Advanced Multi-Modal ML Engine for Deepfake Detection & Media Forensics. "
        "Supports Image, Video, and Audio analysis with asynchronous processing."
    )
)

_security_schemes = {
    "jwt": SecurityScheme(
        type="http",
        scheme="bearer",
        bearerFormat="JWT"
    ),
    "api_key": SecurityScheme(
        type="apiKey",
        name="X-API-Key",
        in_="header"
    )
}

def create_app(config_override=None):
    app = OpenAPI(
        __name__, 
        info=_info, 
        security_schemes=_security_schemes,
        doc_prefix="/openapi",
        doc_ui=True
    )
    if config_override:
        app.config.from_object(config_override)
    else:
        config = get_config()
        app.config.from_object(config)

    os.makedirs("logs", exist_ok=True)
    os.makedirs("weights", exist_ok=True)
    os.makedirs(app.config.get("UPLOAD_FOLDER", "uploads"), exist_ok=True)
    db.init_app(app)
    ma.init_app(app)
    limiter.init_app(app)
    app.config.setdefault("RATELIMIT_DEFAULT", app.config.get("RATE_LIMIT", "30/minute"))
    cors.init_app(
        app,
        origins=app.config.get("CORS_ORIGINS", ["*"]),
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )
    mail.init_app(app)
    redis_url = app.config.get("REDIS_URL", "redis://redis:6379/3")
    redis_client.connection_pool = _redis.ConnectionPool.from_url(
        redis_url, decode_responses=False
    )
    init_celery(app)
    register_middleware(app)
    _register_error_handlers(app)
    app.register_api(health_bp)
    app.register_api(auth_bp)
    app.register_api(detection_bp)
    app.register_api(provenance_bp)
    app.register_api(history_bp)
    app.register_api(community_bp)
    app.register_api(ai_bp)
    @app.route("/", methods=["GET"])
    def root():
        return jsonify({
            "service": app.config.get("APP_NAME", "Divya Drishti"),
            "version": app.config.get("VERSION", "2.0.0"),
        })

    with app.app_context():
        max_retries = 5
        for attempt in range(max_retries):
            try:
                db.create_all()
                logger.success("Database tables initialized")
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Database initialization failed after {max_retries} attempts: {e}")
                else:
                    logger.warning(f"Database not ready (attempt {attempt+1}/{max_retries}). Retrying in 5s...")
                    time.sleep(5)

    with app.app_context():
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(f"{rule.endpoint}: {rule.rule}")
        logger.info(f"Registered routes: \n" + "\n".join(sorted(routes)))
    logger.info(f"DeepTrace ML Engine v{app.config.get('VERSION', '2.0.0')} started")
    return app

def _register_error_handlers(app):
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