"""
AI module powered by Google Gemini.

Provides endpoints for advanced multimodal media detection and
an interactive deepfake safety chatbot.
"""
from flask_openapi3 import APIBlueprint, Tag

ai_tag = Tag(
    name="AI Assistant",
    description="Gemini-powered Deepfake detection and safety chatbot"
)

ai_bp = APIBlueprint("ai", __name__, url_prefix="/ai")

from app.ai import routes
