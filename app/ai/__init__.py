from flask_openapi3 import APIBlueprint, Tag

ai_tag = Tag(
    name="AI Assistant",
    description="Gemini-powered Deepfake detection and safety chatbot"
)

ai_bp = APIBlueprint("ai", __name__, url_prefix="/ai")

from app.ai import routes