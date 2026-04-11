import os
import time
from pathlib import Path
from google import genai
from google.genai import types
from flask import current_app
from app.utils.logger import logger

def get_gemini_client():
    """Initializes and returns a Gemini Client."""
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment or settings")
    return genai.Client(api_key=api_key, http_options={'api_version': 'v1'})

def analyze_media_with_gemini(filepath: str, mime_type: str) -> dict:
    """
    Uploads a file to Gemini, asks it whether the media is AI-generated
    and where on the internet it is available, and returns the response.
    """
    client = get_gemini_client()
    gemini_file = None
    try:
        logger.info(f"Uploading file {filepath} to Gemini API...")
        gemini_file = client.files.upload(file=filepath, config={'mime_type': mime_type})
        
        # If it's a video, wait for processing to finish
        if mime_type.startswith("video/"):
            logger.info("Waiting for video processing on Gemini servers...")
            while gemini_file.state.name == "PROCESSING":
                logger.info(".", end="", flush=True)
                time.sleep(5)
                gemini_file = client.files.get(name=gemini_file.name)
            
            if gemini_file.state.name == "FAILED":
                raise RuntimeError("Video processing failed on Gemini servers.")
        
        logger.info(f"File uploaded. State: {gemini_file.state.name}. Sending prompt...")
        
        prompt = (
            "Analyze this media thoroughly. "
            "1. Determine with high precision if this media is AI-generated (deepfake/synthetic) or real. "
            "Point out any artifacts, unnatural movements, inconsistencies, or synthetic clues. "
            "2. Scour the internet to find where this media is available, providing URLs or at least suggesting "
            "platforms where it typically exists if it is a known viral deepfake. "
            "Provide your findings in a structured, professional report."
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[gemini_file, prompt]
        )
        
        return {
            "analysis": response.text,
            "gemini_file_uri": gemini_file.uri,
        }
        
    finally:
        # Cleanup: ALWAYS delete files from Gemini to ensure privacy
        if gemini_file and hasattr(gemini_file, 'name'):
            try:
                client.files.delete(name=gemini_file.name)
                logger.info(f"Deleted temporary file {gemini_file.name} from Gemini API.")
            except Exception as e:
                logger.error(f"Failed to delete Gemini file {gemini_file.name}: {e}")

def chat_with_gemini(message: str, history: list) -> dict:
    """
    Opens a chat session with the user, acting as a deepfake safety guide.
    """
    system_instruction = (
        "You are the official 'DivDrish Platform Safety Guide', a specialized AI assistant. "
        "Your role is to guide users on how to use the DivDrish platform which detects deepfakes "
        "(image, video, audio) using advanced AI models. "
        "You also teach users how to spot AI manipulations, how to be safe in this AI era, "
        "and best practices for digital provenance and internet safety. "
        "Always be polite, educational, and professional. Do not break character."
    )
    
    client = get_gemini_client()
    
    # Format history strictly for pure Gemini format
    gemini_history = []
    
    # Inject system instruction into the conversation context
    instruction_added = False
    
    for i, h in enumerate(history):
        text = h.parts
        # Prepend to the very first user message
        if not instruction_added and h.role != "model":
            text = f"System Guidelines: {system_instruction}\n\nUser: {text}"
            instruction_added = True
            
        if h.role == "model":
            gemini_history.append({"role": "model", "parts": [{"text": text}]})
        else:
            gemini_history.append({"role": "user", "parts": [{"text": text}]})
            
    # If there was no history, the current message gets the system instruction
    final_message = message
    if not instruction_added:
        final_message = f"System Guidelines: {system_instruction}\n\nUser: {message}"
    
    logger.info(f"Starting Gemini Chat with {len(gemini_history)} previous messages.")
    
    chat_session = client.chats.create(
        model="gemini-2.5-flash",
        history=gemini_history
    )
    
    response = chat_session.send_message(final_message)
    
    return {
        "reply": response.text,
        "role": "model"
    }
