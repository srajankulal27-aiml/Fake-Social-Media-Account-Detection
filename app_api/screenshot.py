"""Screenshot processing and multi-backend OCR extraction module.
Processes images strictly in memory without ever writing to disk, database, or logging sensitive data.
Supports Anthropic Claude Vision as primary and local multi-stage Tesseract OCR as fallback.
"""
import io
import os
import re
import json
import base64
import difflib
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from PIL import Image, ImageOps, ImageFilter
from dotenv import load_dotenv

# Load environment configuration (.env)
load_dotenv()

from app_api.quickfill import (
    extract_username,
    parse_metric_value,
    compute_features
)

# Supported MIME types and magic formats
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


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


def validate_image_upload(image_bytes: bytes, filename: str = "", content_type: str = "") -> Image.Image:
    """Validate uploaded image in memory:
    - Size within 5 MB limit
    - File format verified by Pillow
    - Valid RGB conversion
    """
    if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise ValueError("Image size exceeds maximum permitted limit of 5 MB.")
    
    if len(image_bytes) == 0:
        raise ValueError("Uploaded file is empty.")

    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
    except Exception as exc:
        raise ValueError(f"Invalid or corrupted image file: {str(exc)}")

    # Re-open after verify (Pillow requirement)
    img = Image.open(io.BytesIO(image_bytes))
    if img.format and img.format.upper() not in ["JPEG", "PNG", "WEBP", "BMP"]:
        raise ValueError(f"Unsupported image format '{img.format}'. Please upload PNG, JPG, or WebP.")

    return img.convert("RGB")


def strip_code_fences(text: str) -> str:
    """Strip markdown json code fences if present."""
    t = text.strip()
    if t.startswith("```"):
        lines = t.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines).strip()
    return t


def validate_claude_extracted_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate data types and ranges extracted by Claude backend."""
    if not isinstance(data, dict):
        raise ValueError("Claude response is not a valid JSON dictionary.")

    # Check is_instagram_profile
    if not data.get("is_instagram_profile", True):
        raise ValueError("Uploaded image does not appear to be an Instagram-style profile screenshot.")

    validated = {}
    
    # Username: string matching ^[A-Za-z0-9._]{1,30}$ or null
    raw_user = data.get("username")
    if raw_user and isinstance(raw_user, str):
        raw_user = raw_user.strip()
        if raw_user.startswith("@"):
            raw_user = raw_user[1:]
        if re.match(r"^[A-Za-z0-9._]{1,30}$", raw_user):
            validated["username"] = raw_user
        else:
            validated["username"] = None
    else:
        validated["username"] = None

    # Full name: string or null
    fn = data.get("full_name")
    validated["full_name"] = str(fn).strip() if (fn and isinstance(fn, str)) else None

    # Bio: string or null
    bio = data.get("bio")
    validated["bio"] = str(bio).strip() if (bio and isinstance(bio, str)) else None

    # Counts: non-negative integers or null
    for count_key in ["posts", "followers", "following"]:
        val = data.get(count_key)
        if val is not None:
            try:
                # Handle potential string format from LLM
                if isinstance(val, str):
                    parsed_val = parse_metric_value(val)
                else:
                    parsed_val = int(val)
                validated[count_key] = max(0, parsed_val) if parsed_val is not None else None
            except (ValueError, TypeError):
                validated[count_key] = None
        else:
            validated[count_key] = None

    # Flags: true/false/null
    for flag_key in ["is_private", "has_custom_profile_picture", "external_url_in_bio"]:
        val = data.get(flag_key)
        if isinstance(val, bool):
            validated[flag_key] = val
        elif val in [1, "1", "true", "True"]:
            validated[flag_key] = True
        elif val in [0, "0", "false", "False"]:
            validated[flag_key] = False
        else:
            validated[flag_key] = None

    return validated


def extract_data_via_claude(image_bytes: bytes, api_key: str) -> Dict[str, Any]:
    """Primary Claude Vision backend.
    Processes in-memory bytes and strictly enforces response JSON schema.
    """
    try:
        import anthropic
    except ImportError:
        raise RuntimeError("anthropic package is not installed.")

    model_name = os.getenv("CLAUDE_MODEL", "claude-3-haiku-20240307")
    client = anthropic.Anthropic(api_key=api_key)
    
    # Detect media type
    try:
        with Image.open(io.BytesIO(image_bytes)) as probe:
            fmt = (probe.format or "JPEG").lower()
            if fmt == "jpg":
                fmt = "jpeg"
            media_type = f"image/{fmt}"
    except Exception:
        media_type = "image/jpeg"

    b64_data = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (
        "Read this social media profile screenshot. Return ONLY JSON with keys: "
        "username (string or null), full_name (string or null), bio (string or null), "
        "posts (integer or null), followers (integer or null), following (integer or null), "
        "is_private (true/false/null), has_custom_profile_picture (true/false/null; false only for a flat grey default silhouette), "
        "external_url_in_bio (true/false/null), is_instagram_profile (true/false). "
        "Convert 1.2K to 1200 and 3.4M to 3400000. Use null for anything not clearly visible; "
        "never guess or invent. Do not identify the person or describe their face."
    )

    try:
        response = client.messages.create(
            model=model_name,
            max_tokens=600,
            temperature=0.0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64_data,
                            },
                        },
                        {"type": "text", "text": prompt}
                    ],
                }
            ],
        )
    except anthropic.AuthenticationError:
        raise ValueError("Invalid Anthropic API key. Authentication failed.")
    except anthropic.RateLimitError:
        raise ValueError("Anthropic rate limit exceeded. Please try again shortly.")
    except anthropic.APIConnectionError:
        raise RuntimeError("Network connection error communicating with Anthropic API.")
    except Exception as exc:
        raise RuntimeError(f"Anthropic API call failed: {str(exc)}")

    content = response.content[0].text
    cleaned = strip_code_fences(content)

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError("No JSON object could be extracted from Claude output.")

    raw_json = json.loads(match.group(0))
    return validate_claude_extracted_json(raw_json)


def inspect_avatar_region(img: Image.Image) -> Optional[bool]:
    """Estimate if avatar is custom vs default grey placeholder using pixel statistics.
    Inspects standard top-left/top-center circular avatar zone.
    No face detection or facial recognition.
    Returns: True (custom), False (default grey), or None (unconfident).
    """
    w, h = img.size
    # Avatar is typically in the upper 15-35% region
    # Assume avatar radius ~ w * 0.1 to 0.15 in top-left quadrant
    box = (int(w * 0.04), int(h * 0.08), int(w * 0.32), int(h * 0.35))
    try:
        crop = img.crop(box).convert("RGB")
        arr = np.array(crop, dtype=np.float32)
        if arr.size == 0:
            return None

        # Check standard deviation of color channels (R, G, B)
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        color_diff = np.abs(r - g) + np.abs(g - b) + np.abs(r - b)
        near_grey_fraction = float(np.mean(color_diff < 15.0))
        overall_std = float(np.std(arr))

        # Flat grey default silhouettes have virtually 100% near-grey pixels (r ~= g ~= b)
        if near_grey_fraction > 0.92:
            return False
        # Colorful or diverse photos are custom
        if near_grey_fraction < 0.75:
            return True
        return None
    except Exception:
        return None


def generate_ocr_preprocessed_variants(img: Image.Image) -> List[Tuple[str, Image.Image]]:
    """Produce multiple image preprocessing variants to maximize OCR accuracy
    across light mode, dark mode, low-resolution and high-contrast mobile screenshots.
    """
    variants = []
    rgb = img.convert("RGB")
    gray = rgb.convert("L")
    w, h = gray.size

    # 1. 2x upscale grayscale autocontrast
    scale2 = gray.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
    variants.append(("gray_2x", ImageOps.autocontrast(scale2)))

    # 2. Inverted (Dark Mode support)
    # Check if background is mostly dark (mean brightness < 128)
    is_dark = np.mean(np.array(gray)) < 120
    if is_dark:
        inverted = ImageOps.invert(scale2)
        variants.append(("inverted_dark", ImageOps.autocontrast(inverted)))
    else:
        inverted = ImageOps.invert(scale2)
        variants.append(("inverted_light", inverted))

    # 3. 3x upscale high-contrast threshold
    scale3 = gray.resize((w * 3, h * 3), Image.Resampling.LANCZOS)
    thresh = scale3.point(lambda p: 255 if p > 155 else 0)
    variants.append(("thresh_3x", thresh))

    return variants


def extract_data_via_tesseract(image_bytes: bytes) -> Dict[str, Any]:
    """Tesseract OCR fallback backend.
    Uses pytesseract.image_to_data across preprocessing variants.
    Fuzzy-matches labels ('posts', 'followers', 'following') with difflib >= 0.7.
    Extracts number directly above each label (or beside as fallback).
    Never invents or returns zeros for unlocated fields.
    """
    if pytesseract is None:
        raise RuntimeError("Tesseract OCR is not installed or configured on the system.")

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    variants = generate_ocr_preprocessed_variants(img)

    best_counts: Dict[str, Optional[int]] = {"posts": None, "followers": None, "following": None}
    best_username: Optional[str] = None
    best_fullname: Optional[str] = None
    accumulated_texts: List[str] = []
    
    label_keys = ["posts", "followers", "following"]

    for var_name, var_img in variants:
        try:
            # 1. Image to data dataframe/dict
            data = pytesseract.image_to_data(var_img, output_type=pytesseract.Output.DICT)
            raw_text = pytesseract.image_to_string(var_img)
            accumulated_texts.append(raw_text)

            n_boxes = len(data["text"])
            boxes = []
            for i in range(n_boxes):
                txt = data["text"][i].strip()
                if txt:
                    boxes.append({
                        "text": txt,
                        "left": data["left"][i],
                        "top": data["top"][i],
                        "width": data["width"][i],
                        "height": data["height"][i],
                    })

            # Fuzzy match labels
            # Match each box against posts, followers, following
            for target in label_keys:
                if best_counts[target] is not None:
                    continue

                for b in boxes:
                    clean_word = re.sub(r"[^\w]", "", b["text"].lower())
                    if not clean_word:
                        continue
                    sim = difflib.SequenceMatcher(None, clean_word, target).ratio()
                    if sim >= 0.70:
                        # Located label! Look for number directly ABOVE label
                        # Candidate: box with center_x close to label center_x, and top < label top
                        label_cx = b["left"] + b["width"] / 2.0
                        label_top = b["top"]

                        above_candidates = []
                        beside_candidates = []

                        for cand in boxes:
                            if cand == b:
                                continue
                            cand_cx = cand["left"] + cand["width"] / 2.0
                            cand_cy = cand["top"] + cand["height"] / 2.0

                            # Above: vertical gap within 1.8x height, horizontal offset small
                            if cand["top"] < label_top and (label_top - (cand["top"] + cand["height"])) < (b["height"] * 2.2):
                                if abs(cand_cx - label_cx) < (b["width"] * 1.2):
                                    above_candidates.append(cand)

                            # Beside: same vertical band, left of label
                            if abs(cand_cy - (b["top"] + b["height"] / 2.0)) < (b["height"] * 0.8):
                                if cand["left"] < b["left"] and (b["left"] - (cand["left"] + cand["width"])) < (b["width"] * 1.5):
                                    beside_candidates.append(cand)

                        # Try above candidates first
                        val = None
                        for c in above_candidates:
                            parsed = parse_metric_value(c["text"])
                            if parsed is not None:
                                val = parsed
                                break

                        # Fallback to beside candidates
                        if val is None:
                            for c in beside_candidates:
                                parsed = parse_metric_value(c["text"])
                                if parsed is not None:
                                    val = parsed
                                    break

                        if val is not None:
                            best_counts[target] = val

            # Find username: largest text in upper region of the image
            upper_boxes = [b for b in boxes if b["top"] < (var_img.height * 0.35)]
            if upper_boxes and not best_username:
                # Sort by font height descending
                sorted_by_size = sorted(upper_boxes, key=lambda b: b["height"] * b["width"], reverse=True)
                for b in sorted_by_size:
                    cand_user = extract_username(b["text"])
                    if cand_user:
                        best_username = cand_user
                        break

            # Find full name: text below avatar/counts
            lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
            for l in lines[:6]:
                if not best_fullname and not re.search(r"\d", l) and len(l) > 2 and l.lower() != (best_username or "").lower():
                    # Reject words like Edit Profile, Posts, Followers
                    if not any(k in l.lower() for k in ["edit profile", "posts", "followers", "following", "message", "contact"]):
                        best_fullname = l

        except Exception:
            continue

    # Fallback to regex on accumulated raw text if count missing
    combined_raw = "\n".join(accumulated_texts)
    for target in label_keys:
        if best_counts[target] is None:
            # Pattern: 120 posts or posts: 120
            p1 = re.search(r"([\d.,]+[kKmMbB]?)\s*" + target + r"\b", combined_raw, re.IGNORECASE)
            if p1:
                best_counts[target] = parse_metric_value(p1.group(1))

    # Detect private
    is_private = True if re.search(r"\b(this account is private|private account)\b", combined_raw, re.IGNORECASE) else (False if re.search(r"\b(posts|tagged)\b", combined_raw, re.IGNORECASE) else None)

    # Detect external URL in text
    url_match = re.search(r"(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.-]+\.(?:com|org|net|io|me|co|link|app)[^\s]*)", combined_raw, re.IGNORECASE)
    has_url = True if url_match else False

    # Extract bio lines
    bio_lines = []
    lines = [l.strip() for l in combined_raw.splitlines() if l.strip()]
    record_bio = False
    for l in lines:
        if any(w in l.lower() for w in ["followers", "following", "posts", "edit profile"]):
            record_bio = True
            continue
        if record_bio:
            if any(w in l.lower() for w in ["tagged", "suggested", "about this account"]):
                break
            if len(l) > 3:
                bio_lines.append(l)
    bio = "\n".join(bio_lines[:4]) if bio_lines else None

    # Avatar check via pixel statistics
    custom_pic = inspect_avatar_region(img)

    return {
        "username": best_username,
        "full_name": best_fullname,
        "bio": bio,
        "posts": best_counts["posts"],
        "followers": best_counts["followers"],
        "following": best_counts["following"],
        "is_private": is_private,
        "has_custom_profile_picture": custom_pic,
        "external_url_in_bio": has_url,
        "raw_ocr_text": combined_raw[:1500] if combined_raw else ""
    }


def compute_confidence(val: Any) -> str:
    """Return confidence rating ('high', 'low', 'none') for an extracted field."""
    if val is None:
        return "none"
    return "high"


def extract_from_screenshot(image_bytes: bytes, filename: str = "", content_type: str = "") -> Dict[str, Any]:
    """Main extraction coordinator:
    - Validates image upload
    - Determines backend: 'claude', 'tesseract', or 'auto' (via SCREENSHOT_BACKEND)
    - Automatically falls back to Tesseract if Claude fails or is unconfigured
    - Formats per-field confidence, warnings, and model-ready derived features.
    """
    # 1. Upload validation
    validated_img = validate_image_upload(image_bytes, filename=filename, content_type=content_type)

    backend_pref = os.getenv("SCREENSHOT_BACKEND", "auto").strip().lower()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()

    backend_used = "tesseract"
    warnings: List[str] = []
    parsed_data: Dict[str, Any] = {}
    raw_ocr = None

    # Determine execution route
    use_claude = False
    if backend_pref == "claude":
        if not anthropic_key:
            warnings.append("SCREENSHOT_BACKEND set to 'claude' but ANTHROPIC_API_KEY is not configured. Falling back to Tesseract.")
        else:
            use_claude = True
    elif backend_pref == "tesseract":
        use_claude = False
    else:  # 'auto'
        if anthropic_key:
            use_claude = True

    # Attempt Claude
    if use_claude:
        try:
            parsed_data = extract_data_via_claude(image_bytes, anthropic_key)
            backend_used = "claude"
        except Exception as exc:
            warnings.append(f"Claude Vision extraction failed ({str(exc)}). Automatically fell back to Tesseract OCR.")
            backend_used = "tesseract"

    # Run Tesseract if chosen or if Claude failed
    if backend_used == "tesseract":
        try:
            parsed_data = extract_data_via_tesseract(image_bytes)
            raw_ocr = parsed_data.get("raw_ocr_text", "")
        except Exception as exc:
            raise RuntimeError(f"OCR extraction engine failed: {str(exc)}")

    # Build per-field confidence
    field_keys = ["username", "full_name", "bio", "posts", "followers", "following", "is_private", "has_custom_profile_picture", "external_url_in_bio"]
    confidence: Dict[str, str] = {}
    for k in field_keys:
        v = parsed_data.get(k)
        if v is None:
            confidence[k] = "none"
        else:
            confidence[k] = "high" if backend_used == "claude" else ("high" if k in ["posts", "followers", "following"] and v is not None else "low")

    # Flag missing required fields in warnings
    missing = [k for k in ["username", "posts", "followers", "following", "is_private", "has_custom_profile_picture"] if parsed_data.get(k) is None]
    if missing:
        warnings.append(f"Could not reliably detect: {', '.join(missing)}. Please confirm or enter manually before analyzing.")

    # Compute derived 11 model features if minimal fields are present (use safe defaults for derivation only)
    u = parsed_data.get("username") or ""
    fn = parsed_data.get("full_name") or ""
    bio = parsed_data.get("bio") or ""
    p = parsed_data.get("posts") if parsed_data.get("posts") is not None else 0
    f_ers = parsed_data.get("followers") if parsed_data.get("followers") is not None else 0
    f_ing = parsed_data.get("following") if parsed_data.get("following") is not None else 0
    p_pic = 1 if parsed_data.get("has_custom_profile_picture") is not False else 0
    is_priv = 1 if parsed_data.get("is_private") is True else 0

    derived = compute_features(
        username=u,
        full_name=fn,
        bio=bio,
        posts=p,
        followers=f_ers,
        following=f_ing,
        profile_pic=p_pic,
        is_private=is_priv
    )

    return {
        "backend_used": backend_used,
        "warnings": warnings,
        "confidence": confidence,
        "parsed": parsed_data,
        "features": derived,
        "derived_features": derived,
        "raw_ocr_text": raw_ocr
    }
