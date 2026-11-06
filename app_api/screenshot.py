"""Screenshot processing and OCR extraction module.
Processes images strictly in memory without ever writing to disk, database, or logging sensitive data.
Supports Tesseract OCR locally and an optional Anthropic Claude Vision backend.
"""
import io
import os
import re
import base64
from typing import Dict, Any, Optional
from PIL import Image, ImageOps, ImageFilter
from dotenv import load_dotenv

# Load optional .env
load_dotenv()

from app_api.quickfill import (
    extract_username,
    parse_counts,
    compute_features
)

# Detect Tesseract executable if installed
def _configure_tesseract():
    try:
        import pytesseract
        candidates = [
            os.getenv("TESSERACT_PATH"),
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Users\sraja\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
        ]
        for c in candidates:
            if c and os.path.exists(c):
                pytesseract.pytesseract.tesseract_cmd = c
                return pytesseract
        return pytesseract
    except ImportError:
        return None

pytesseract = _configure_tesseract()


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """Memory-only preprocessing to maximize OCR accuracy:
    - Converts to Grayscale
    - Resizes if small
    - Contrast auto-contrast & thresholding
    """
    gray = image.convert("L")
    w, h = gray.size
    if w < 600:
        gray = gray.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
    gray = ImageOps.autocontrast(gray)
    return gray


def extract_text_via_tesseract(image_bytes: bytes) -> str:
    """Extract raw text from in-memory image bytes using pytesseract.
    Never writes image to disk.
    """
    if pytesseract is None:
        raise RuntimeError("pytesseract module is not installed.")
    
    with Image.open(io.BytesIO(image_bytes)) as img:
        processed = preprocess_image_for_ocr(img)
        text = pytesseract.image_to_string(processed)
        return text or ""


def extract_data_via_claude(image_bytes: bytes, api_key: str) -> Dict[str, Any]:
    """Optional Claude Vision extraction backend for higher fidelity parsing.
    Sends in-memory bytes directly to Anthropic API.
    """
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package not installed.")

    client = anthropic.Anthropic(api_key=api_key)
    b64_data = base64.b64encode(image_bytes).decode("utf-8")
    
    prompt = (
        "Analyze this social media profile screenshot and return JSON with keys: "
        "'username' (string or null), 'full_name' (string or null), 'bio' (string or null), "
        "'posts' (integer or null), 'followers' (integer or null), 'following' (integer or null), "
        "'profile_pic' (1 if avatar is set, 0 if default placeholder), "
        "'is_private' (1 if account is private, 0 if public). "
        "Return ONLY valid JSON."
    )
    
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=500,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": b64_data,
                        },
                    },
                    {"type": "text", "text": prompt}
                ],
            }
        ],
    )
    
    content_text = message.content[0].text
    import json
    # Extract JSON block
    match = re.search(r"\{.*\}", content_text, re.DOTALL)
    if match:
        return json.loads(match.group(0))
    return {}


def parse_profile_text_to_dict(text: str) -> Dict[str, Any]:
    """Parse text extracted via OCR into structured profile attributes."""
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    counts = parse_counts(text)
    
    # Try finding username
    detected_user = None
    for line in lines[:5]:
        extracted = extract_username(line)
        if extracted:
            detected_user = extracted
            break

    # Check for private indicator
    is_private = 1 if re.search(r"\b(private account|this account is private)\b", text, re.IGNORECASE) else 0

    # Bio is text after counts or lines in middle
    bio = ""
    if len(lines) > 2:
        bio = "\n".join(lines[2:8])

    return {
        "username": detected_user or "",
        "full_name": lines[1] if len(lines) > 1 and not lines[1].isdigit() else "",
        "bio": bio,
        "posts": counts["posts"] if counts["posts"] is not None else 0,
        "followers": counts["followers"] if counts["followers"] is not None else 0,
        "following": counts["following"] if counts["following"] is not None else 0,
        "profile_pic": 1,
        "is_private": is_private,
        "ocr_text": text
    }


def extract_from_screenshot(image_bytes: bytes) -> Dict[str, Any]:
    """Orchestrates in-memory extraction.
    Tries Claude if ANTHROPIC_API_KEY is configured; otherwise uses Tesseract OCR.
    Always falls back gracefully.
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            data = extract_data_via_claude(image_bytes, anthropic_key)
            if data and data.get("username"):
                features = compute_features(
                    username=data.get("username", ""),
                    full_name=data.get("full_name", ""),
                    bio=data.get("bio", ""),
                    posts=data.get("posts", 0) or 0,
                    followers=data.get("followers", 0) or 0,
                    following=data.get("following", 0) or 0,
                    profile_pic=data.get("profile_pic", 1) or 1,
                    is_private=data.get("is_private", 0) or 0
                )
                return {
                    "backend": "claude",
                    "parsed": data,
                    "features": features,
                    "error": None
                }
        except Exception:
            pass  # Fallback to Tesseract OCR

    try:
        raw_text = extract_text_via_tesseract(image_bytes)
        parsed = parse_profile_text_to_dict(raw_text)
        features = compute_features(
            username=parsed["username"],
            full_name=parsed["full_name"],
            bio=parsed["bio"],
            posts=parsed["posts"],
            followers=parsed["followers"],
            following=parsed["following"],
            profile_pic=parsed["profile_pic"],
            is_private=parsed["is_private"]
        )
        return {
            "backend": "tesseract",
            "parsed": parsed,
            "features": features,
            "error": None
        }
    except Exception as exc:
        return {
            "backend": "none",
            "parsed": {},
            "features": compute_features(""),
            "error": str(exc)
        }

