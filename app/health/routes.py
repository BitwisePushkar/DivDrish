"""
Health check routes blueprint.

Public endpoint — no authentication required.
"""
import torch
from flask import Blueprint, jsonify
from app.config.settings import get_config
from app.detection.controllers import get_detectors

health_bp = Blueprint("health", __name__)


@health_bp.route("/health", methods=["GET"])
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
