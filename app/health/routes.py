"""
Health check routes blueprint.

Public endpoint — no authentication required.
"""
from pydantic import BaseModel
import torch
from flask import jsonify
from app.config.settings import get_config
from app.detection.controllers import get_detectors

from flask_openapi3 import APIBlueprint, Tag

_tag = Tag(name="Health", description="System health and status monitoring")
health_bp = APIBlueprint("health", __name__)


class HealthResponse(BaseModel):
    status: str
    version: str
    models_loaded: dict
    gpu_available: bool


@health_bp.get(
    "/health",
    tags=[_tag],
    summary="Check system health",
    responses={200: HealthResponse}
)
def health():
    """System health check — returns model status and GPU info."""
    config = get_config()
    detectors = get_detectors()

    return jsonify({
        "status": "ok",
        "version": config.VERSION,
        "models_loaded": {k: v.loaded for k, v in detectors.items()},
        "gpu_available": torch.cuda.is_available(),
    })
