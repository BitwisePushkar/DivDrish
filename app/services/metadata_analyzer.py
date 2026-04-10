"""
Metadata provenance analyzer.

Extracts and analyzes file metadata (EXIF, container info, encoder
signatures) to detect signs of manipulation or synthetic origin.

Enhanced with AI-generated content detection (Stable Diffusion,
DALL-E, Midjourney, ComfyUI, Automatic1111 signatures).
"""
import struct
from pathlib import Path
from typing import Tuple, List
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from app.utils.logger import logger


# ─── Suspicious software patterns ────────────────────────

SUSPICIOUS_SOFTWARE = [
    "photoshop", "gimp", "affinity", "deepfacelab", "faceswap",
    "fakeapp", "stable diffusion", "midjourney", "dall-e", "comfyui",
    "automatic1111", "novelai", "artbreeder", "runway",
]

# ─── AI generation markers (enhanced) ────────────────────

AI_GENERATION_MARKERS = [
    "stable diffusion", "dall-e", "midjourney", "comfyui",
    "automatic1111", "invokeai", "novelai", "dream studio",
    "leonardo.ai", "firefly", "ideogram", "flux",
    "kandinsky", "deepai", "craiyon", "bluewillow",
]

AI_PNG_KEYS = [
    "parameters", "prompt", "negative_prompt", "workflow",
    "comfui_prompt", "sd-metadata", "generation_data",
    "dream", "ai_metadata", "source", "model",
]

SUSPICIOUS_EXIF_SIGNS = [
    "completely missing EXIF data",
    "no camera manufacturer info",
    "software modification detected",
    "GPS data stripped or inconsistent",
    "creation date missing",
    "modification date but no creation date",
]


# ─── Public API ───────────────────────────────────────────

def analyze_metadata(file_path: str, media_type: str) -> dict:
    """
    Analyze file metadata and return provenance information.

    Returns:
        dict with keys:
            anomalies: List[str]
            provenance_score: float (0=highly suspicious, 1=authentic-looking)
            metadata_extracted: dict of raw metadata
            ai_generation_indicators: List[str] (NEW)
    """
    path = Path(file_path)

    if media_type == "image":
        return _analyze_image_metadata(path)
    elif media_type == "video":
        return _analyze_video_metadata(path)
    elif media_type == "audio":
        return _analyze_audio_metadata(path)

    return {
        "anomalies": [],
        "provenance_score": 0.5,
        "metadata_extracted": {},
        "ai_generation_indicators": [],
    }


# ─── Image metadata ──────────────────────────────────────

def _analyze_image_metadata(path: Path) -> dict:
    anomalies: List[str] = []
    extracted: dict = {}
    ai_indicators: List[str] = []
    penalty = 0.0

    try:
        img = Image.open(path)
        extracted["format"] = img.format
        extracted["mode"] = img.mode
        extracted["size"] = f"{img.width}x{img.height}"

        exif_data = img.getexif()

        if not exif_data:
            anomalies.append("No EXIF data found — common in AI-generated images")
            ai_indicators.append("Missing EXIF data (typical of AI-generated images)")
            penalty += 0.30
        else:
            decoded_exif = {}
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                try:
                    decoded_exif[tag_name] = str(value)
                except Exception:
                    decoded_exif[tag_name] = "<binary>"

            extracted["exif"] = decoded_exif

            # Check for camera info
            make = decoded_exif.get("Make", "")
            model = decoded_exif.get("Model", "")
            if not make and not model:
                anomalies.append("No camera make/model — unlikely for genuine photos")
                ai_indicators.append("No camera hardware info found")
                penalty += 0.15

            # Check for software modification
            software = decoded_exif.get("Software", "").lower()
            if software:
                extracted["software"] = software
                for sus in SUSPICIOUS_SOFTWARE:
                    if sus in software:
                        anomalies.append(
                            f"Edited with suspicious software: {software}"
                        )
                        penalty += 0.20
                        break
                for marker in AI_GENERATION_MARKERS:
                    if marker in software:
                        ai_indicators.append(
                            f"AI generation software detected in EXIF: {software}"
                        )
                        penalty += 0.15
                        break

            # Check UserComment for AI indicators
            user_comment = decoded_exif.get("UserComment", "").lower()
            if user_comment:
                for marker in AI_GENERATION_MARKERS:
                    if marker in user_comment:
                        ai_indicators.append(
                            f"AI generation marker in UserComment: {user_comment[:80]}"
                        )
                        penalty += 0.15
                        break
                if "ai generated" in user_comment or "digital art" in user_comment:
                    ai_indicators.append(
                        f"AI generation label in UserComment: {user_comment[:80]}"
                    )
                    penalty += 0.10

            # Check date consistency
            date_orig = decoded_exif.get("DateTimeOriginal")
            date_modified = decoded_exif.get("DateTime")

            if not date_orig and not date_modified:
                anomalies.append("No timestamp data found")
                penalty += 0.10
            elif date_modified and not date_orig:
                anomalies.append(
                    "Modification date present but no original capture date"
                )
                penalty += 0.15

            # Check for GPS
            gps_info = exif_data.get_ifd(0x8825)  # GPSInfo IFD
            if gps_info:
                extracted["has_gps"] = True
            else:
                extracted["has_gps"] = False

        # Check for unusual color profiles
        icc = img.info.get("icc_profile")
        if icc and len(icc) > 10:
            extracted["has_icc_profile"] = True
        else:
            extracted["has_icc_profile"] = False

        # Structural checks — PNG chunks (enhanced for AI detection)
        if img.format == "PNG":
            text_chunks = {k: v for k, v in img.info.items() if isinstance(v, str)}
            if text_chunks:
                extracted["png_text_chunks"] = text_chunks

                # Check for AI generation metadata in PNG chunks
                for key, val in text_chunks.items():
                    key_lower = key.lower()
                    val_lower = val.lower()

                    # Check for known AI tool keys
                    for ai_key in AI_PNG_KEYS:
                        if ai_key in key_lower:
                            ai_indicators.append(
                                f"AI generation metadata found: {key}={val[:100]}"
                            )
                            penalty += 0.20
                            break

                    # Check for AI tool names in values
                    for marker in AI_GENERATION_MARKERS:
                        if marker in val_lower:
                            ai_indicators.append(
                                f"AI tool reference in PNG metadata: {val[:100]}"
                            )
                            penalty += 0.15
                            break

                    # Original suspicious software check
                    for sus in SUSPICIOUS_SOFTWARE:
                        if sus in val_lower:
                            anomalies.append(
                                f"PNG metadata references: {val[:60]}"
                            )
                            penalty += 0.15
                            break

    except Exception as e:
        logger.warning(f"Image metadata extraction failed: {e}")
        anomalies.append(f"Metadata extraction error: {str(e)}")
        penalty += 0.10

    provenance_score = max(0.0, min(1.0, 1.0 - penalty))
    return {
        "anomalies": anomalies,
        "provenance_score": round(provenance_score, 3),
        "metadata_extracted": extracted,
        "ai_generation_indicators": ai_indicators,
    }


# ─── Video metadata ──────────────────────────────────────

def _analyze_video_metadata(path: Path) -> dict:
    anomalies: List[str] = []
    extracted: dict = {}
    ai_indicators: List[str] = []
    penalty = 0.0

    try:
        import cv2

        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            anomalies.append("Failed to open video container")
            return {
                "anomalies": anomalies,
                "provenance_score": 0.5,
                "metadata_extracted": {},
                "ai_generation_indicators": [],
            }

        extracted["fps"] = round(cap.get(cv2.CAP_PROP_FPS), 2)
        extracted["frame_count"] = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        extracted["width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        extracted["height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        extracted["codec"] = _decode_fourcc(int(cap.get(cv2.CAP_PROP_FOURCC)))
        cap.release()

        # Check for re-encoding markers
        duration = extracted["frame_count"] / max(extracted["fps"], 1)
        extracted["duration_sec"] = round(duration, 2)

        if extracted["fps"] == 0:
            anomalies.append("FPS reported as 0 — corrupted or synthetic container")
            penalty += 0.25

        # Unusual resolutions (not standard aspect ratios)
        w, h = extracted["width"], extracted["height"]
        aspect = w / max(h, 1)
        standard_aspects = [16 / 9, 4 / 3, 1.0, 9 / 16, 3 / 4, 21 / 9]
        if not any(abs(aspect - s) < 0.05 for s in standard_aspects):
            anomalies.append(
                f"Non-standard aspect ratio ({aspect:.2f}) — possible crop/edit"
            )
            penalty += 0.10

        # Very short video (likely a deepfake clip)
        if duration < 2.0:
            anomalies.append(
                f"Very short duration ({duration:.1f}s) — common in generated clips"
            )
            ai_indicators.append("Very short duration typical of AI-generated video")
            penalty += 0.10

        # File container analysis via raw bytes
        container_info = _analyze_video_container(path)
        extracted.update(container_info.get("extracted", {}))
        anomalies.extend(container_info.get("anomalies", []))
        ai_indicators.extend(container_info.get("ai_indicators", []))
        penalty += container_info.get("penalty", 0.0)

    except Exception as e:
        logger.warning(f"Video metadata extraction failed: {e}")
        anomalies.append(f"Metadata extraction error: {str(e)}")
        penalty += 0.10

    provenance_score = max(0.0, min(1.0, 1.0 - penalty))
    return {
        "anomalies": anomalies,
        "provenance_score": round(provenance_score, 3),
        "metadata_extracted": extracted,
        "ai_generation_indicators": ai_indicators,
    }


def _analyze_video_container(path: Path) -> dict:
    """Parse MP4 container for encoder string."""
    anomalies = []
    extracted = {}
    ai_indicators = []
    penalty = 0.0

    try:
        with open(path, "rb") as f:
            header = f.read(4096)

        # Check for known encoder strings in header
        header_str = header.decode("ascii", errors="replace").lower()
        for sus in SUSPICIOUS_SOFTWARE:
            if sus in header_str:
                anomalies.append(f"Video container references: {sus}")
                penalty += 0.15
                break

        # Check for AI generation tool references
        for marker in AI_GENERATION_MARKERS:
            if marker in header_str:
                ai_indicators.append(f"AI tool reference in video container: {marker}")
                penalty += 0.15
                break

        # Extract encoder from ftyp/moov atoms
        if b"ftyp" in header[:16]:
            ftyp_brand = header[8:12].decode("ascii", errors="replace")
            extracted["container_brand"] = ftyp_brand

    except Exception:
        pass

    return {
        "anomalies": anomalies,
        "extracted": extracted,
        "ai_indicators": ai_indicators,
        "penalty": penalty,
    }


def _decode_fourcc(fourcc: int) -> str:
    """Decode a FourCC integer into a human-readable codec string."""
    try:
        return "".join([chr((fourcc >> (8 * i)) & 0xFF) for i in range(4)])
    except Exception:
        return "unknown"


# ─── Audio metadata ──────────────────────────────────────

def _analyze_audio_metadata(path: Path) -> dict:
    anomalies: List[str] = []
    extracted: dict = {}
    ai_indicators: List[str] = []
    penalty = 0.0

    try:
        import librosa
        import soundfile as sf

        info = sf.info(str(path))
        extracted["format"] = info.format
        extracted["subtype"] = info.subtype
        extracted["channels"] = info.channels
        extracted["samplerate"] = info.samplerate
        extracted["duration_sec"] = round(info.duration, 2)
        extracted["frames"] = info.frames

        # TTS/synth audio is almost always mono 16kHz or 22kHz
        if info.channels == 1 and info.samplerate in (16000, 22050):
            anomalies.append(
                f"Mono {info.samplerate}Hz — common TTS output format"
            )
            ai_indicators.append(
                f"Audio format matches TTS output: mono {info.samplerate}Hz"
            )
            penalty += 0.15

        # Very short audio
        if info.duration < 1.0:
            anomalies.append("Audio shorter than 1 second")
            penalty += 0.10

        # Check for constant bitrate anomalies (WAV should be uncompressed)
        if info.format == "WAV" and "PCM" not in info.subtype:
            anomalies.append(
                f"WAV with non-PCM encoding ({info.subtype}) — possible re-encoding"
            )
            penalty += 0.10

        # Check for metadata tags
        _check_audio_tags(path, anomalies, extracted, ai_indicators)

    except Exception as e:
        logger.warning(f"Audio metadata extraction failed: {e}")
        anomalies.append(f"Metadata extraction error: {str(e)}")
        penalty += 0.10

    provenance_score = max(0.0, min(1.0, 1.0 - penalty))
    return {
        "anomalies": anomalies,
        "provenance_score": round(provenance_score, 3),
        "metadata_extracted": extracted,
        "ai_generation_indicators": ai_indicators,
    }


def _check_audio_tags(
    path: Path, anomalies: list, extracted: dict, ai_indicators: list
):
    """Check for ID3/tag metadata in audio files."""
    try:
        with open(path, "rb") as f:
            header = f.read(128)

        # Check for ID3 tag
        if header[:3] == b"ID3":
            extracted["has_id3"] = True
        else:
            extracted["has_id3"] = False
            if path.suffix.lower() in (".mp3",):
                anomalies.append("MP3 without ID3 tag — metadata stripped")

        # Check for AI tool references in header
        header_str = header.decode("ascii", errors="replace").lower()
        for marker in AI_GENERATION_MARKERS:
            if marker in header_str:
                ai_indicators.append(f"AI tool reference in audio header: {marker}")
                break

    except Exception:
        pass
