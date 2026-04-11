from pydantic import BaseModel, Field
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the sender, either 'user' or 'model'")
    parts: str = Field(..., description="The message content")

class ChatBotRequest(BaseModel):
    message: str = Field(..., description="The new message from the user")
    history: Optional[List[ChatMessage]] = Field(default=[], description="Past conversation history to maintain context")

class DetectMediaResponse(BaseModel):
    status: str = Field("success")
    message: str = Field("Media analyzed successfully")
    data: dict = Field(..., description="Gemini analysis results")

class ChatBotResponse(BaseModel):
    status: str = Field("success")
    message: str = Field("Chat completed")
    data: dict = Field(..., description="Response from the deepfake safety assistant")
