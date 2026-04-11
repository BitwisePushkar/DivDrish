import os
import time
import json
from pathlib import Path
from google import genai
from google.genai import types
from flask import current_app
from app.utils.logger import logger

def get_gemini_client():
    api_key = current_app.config.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in environment or settings")
    return genai.Client(api_key=api_key)

def analyze_media_with_gemini(filepath: str, mime_type: str) -> dict:
    client = get_gemini_client()
    gemini_file = None
    try:
        logger.info(f"Uploading file {filepath} to Gemini API...")
        gemini_file = client.files.upload(file=filepath, config={'mime_type': mime_type})
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
            "You are an expert digital forensics analyst specializing in deepfake and AI-generated media detection. "
            "Analyze the provided media with extreme scrutiny to determine if it is AI-generated (synthetic) or real. "
            "Look closely for the following common AI artifacts:\n"
            "- Unnatural textures, glowing/plastic skin, or overly smooth rendering\n"
            "- Asymmetries in faces, mismatched eyes, ears, or glasses\n"
            "- Anatomical errors (e.g., wrong number of fingers, weird joints, merging limbs, floating hair)\n"
            "- Incoherent or physically impossible backgrounds\n"
            "- Warped text, unreadable signs, or nonsensical background details\n"
            "- Inconsistent lighting or shadows, lacking physical logic\n\n"
            "If you spot ANY of these artifacts, strongly consider the media 'AI-generated' (is_fake: true). "
            "Respond strictly in JSON format matching the following structure:\n"
            "{\n"
            '  "is_fake": boolean (true if synthetic/AI artifacts found, false if authentic),\n'
            '  "confidence": float between 0.0 and 1.0 (how certain you are based on the artifacts),\n'
            '  "recommendation": string (one of "high_risk", "safe", "investigate"),\n'
            '  "artifact_signatures": list of strings (specific artifacts or synthetic clues found, e.g., "Messed up fingers in left hand"),\n'
            '  "internet_footprint": list of strings (URLs or platforms where found online),\n'
            '  "summary": string (a comprehensive professional report of your findings detailing why it is fake or real)\n'
            "}"
        )
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[gemini_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            )
        )
        
        try:
            analysis_data = json.loads(response.text)
        except Exception as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}. Raw response: {response.text}")
            analysis_data = {"summary": response.text, "error": "JSON parse error"}

        return {
            "analysis": analysis_data,
            "gemini_file_uri": gemini_file.uri,
        }  
    finally:
        if gemini_file and hasattr(gemini_file, 'name'):
            try:
                client.files.delete(name=gemini_file.name)
                logger.info(f"Deleted temporary file {gemini_file.name} from Gemini API.")
            except Exception as e:
                logger.error(f"Failed to delete Gemini file {gemini_file.name}: {e}")

def chat_with_gemini(message: str, history: list) -> dict:
    system_instruction = (
        "You are the official 'DivDrish Platform Safety Guide', a specialized AI assistant. "
        "Your role is to guide users on how to use the DivDrish platform which detects deepfakes "
        "(image, video, audio) using advanced AI models. "
        "You also teach users how to spot AI manipulations, how to be safe in this AI era, "
        "and best practices for digital provenance and internet safety. "
        "Always be polite, educational, and professional. Do not break character."
    ) 
    client = get_gemini_client()
    gemini_history = []
    instruction_added = False
    for i, h in enumerate(history):
        text = h.parts
        if not instruction_added and h.role != "model":
            text = f"System Guidelines: {system_instruction}\n\nUser: {text}"
            instruction_added = True
        if h.role == "model":
            gemini_history.append({"role": "model", "parts": [{"text": text}]})
        else:
            gemini_history.append({"role": "user", "parts": [{"text": text}]})
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