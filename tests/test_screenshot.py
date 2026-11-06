"""Unit and integration tests for screenshot extraction module.
Covers:
- Claude backend with mocked responses (valid, fenced, malformed, wrong types, negative, not instagram, errors)
- Tesseract backend execution on real fixtures (profile_genuine.png, profile_fake.png)
- Noise image handling (returns nulls, not zeros)
- Memory-only verification (no files written to disk)
- Live Claude test (optional, runs only when real ANTHROPIC_API_KEY is present)
"""
import io
import os
import json
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from PIL import Image

from app_api.screenshot import (
    extract_from_screenshot,
    validate_image_upload,
    validate_claude_extracted_json,
    strip_code_fences,
    extract_data_via_tesseract,
    extract_data_via_claude,
    pytesseract
)

FIXTURES_DIR = Path("tests/fixtures")


# 1. Claude Backend Unit Tests (Mocked API Responses)

def test_strip_code_fences():
    raw_fence = "```json\n{\"username\": \"test_user\"}\n```"
    assert strip_code_fences(raw_fence) == "{\"username\": \"test_user\"}"
    plain = "{\"username\": \"test_user\"}"
    assert strip_code_fences(plain) == plain


def test_validate_claude_extracted_json_valid():
    raw = {
        "username": "srajankulal27",
        "full_name": "Srajan Kulal",
        "bio": "AI Engineer",
        "posts": 120,
        "followers": 800,
        "following": 400,
        "is_private": False,
        "has_custom_profile_picture": True,
        "external_url_in_bio": True,
        "is_instagram_profile": True
    }
    validated = validate_claude_extracted_json(raw)
    assert validated["username"] == "srajankulal27"
    assert validated["posts"] == 120
    assert validated["followers"] == 800
    assert validated["following"] == 400
    assert validated["is_private"] is False
    assert validated["has_custom_profile_picture"] is True


def test_validate_claude_extracted_json_code_fences_and_strings():
    raw = {
        "username": "@srajankulal27",
        "full_name": "Srajan Kulal",
        "bio": None,
        "posts": "120",
        "followers": "1.2K",
        "following": "300",
        "is_private": "false",
        "has_custom_profile_picture": "true",
        "external_url_in_bio": "false",
        "is_instagram_profile": True
    }
    validated = validate_claude_extracted_json(raw)
    assert validated["username"] == "srajankulal27"
    assert validated["posts"] == 120
    assert validated["followers"] == 1200
    assert validated["following"] == 300
    assert validated["is_private"] is False
    assert validated["has_custom_profile_picture"] is True


def test_validate_claude_extracted_json_rejects_non_instagram():
    raw = {
        "is_instagram_profile": False,
        "username": "random_user"
    }
    with pytest.raises(ValueError, match="does not appear to be an Instagram-style profile screenshot"):
        validate_claude_extracted_json(raw)


def test_validate_claude_extracted_json_wrong_types_and_negatives():
    raw = {
        "username": "invalid user with spaces!",
        "posts": -5,
        "followers": "invalid_number",
        "is_private": "unknown_string",
        "is_instagram_profile": True
    }
    validated = validate_claude_extracted_json(raw)
    assert validated["username"] is None
    assert validated["posts"] == 0  # Clamped to non-negative
    assert validated["followers"] is None
    assert validated["is_private"] is None


@patch("anthropic.Anthropic")
def test_claude_backend_mock_success(mock_anthropic):
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text='```json\n{"username": "test_user", "posts": 50, "followers": 1500, "following": 300, "is_private": false, "has_custom_profile_picture": true, "is_instagram_profile": true}\n```')]
    mock_client.messages.create.return_value = mock_msg

    img = Image.new("RGB", (100, 100), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = extract_data_via_claude(buf.getvalue(), api_key="test_dummy_key")

    assert data["username"] == "test_user"
    assert data["posts"] == 50
    assert data["followers"] == 1500


@patch("anthropic.Anthropic")
def test_claude_backend_fallback_on_api_error(mock_anthropic, monkeypatch):
    monkeypatch.setenv("SCREENSHOT_BACKEND", "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_key")

    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client
    mock_client.messages.create.side_effect = RuntimeError("API Gateway 502 Bad Gateway")

    with open(FIXTURES_DIR / "profile_genuine.png", "rb") as f:
        img_bytes = f.read()

    res = extract_from_screenshot(img_bytes)
    assert res["backend_used"] == "tesseract"
    assert any("Claude Vision extraction failed" in w for w in res["warnings"])
    assert res["parsed"]["username"] == "srajankulal27"


# 2. Tesseract Backend Tests on Real Fixtures

@pytest.mark.skipif(pytesseract is None, reason="Tesseract OCR is not installed")
def test_tesseract_real_fixture_genuine():
    fixture_path = FIXTURES_DIR / "profile_genuine.png"
    assert fixture_path.exists(), "profile_genuine.png fixture is missing"

    with open(fixture_path, "rb") as f:
        img_bytes = f.read()

    res = extract_from_screenshot(img_bytes)
    assert res["backend_used"] == "tesseract"
    parsed = res["parsed"]

    # Exact expected values:
    # username: srajankulal27, 120 posts, 800 followers, 400 following, full name "Srajan Kulal", custom pic, public
    assert parsed["username"] == "srajankulal27"
    assert parsed["posts"] == 120
    assert parsed["followers"] == 800
    assert parsed["following"] == 400
    assert "Srajan" in (parsed["full_name"] or "")
    assert parsed["has_custom_profile_picture"] is True
    assert parsed["is_private"] is False


@pytest.mark.skipif(pytesseract is None, reason="Tesseract OCR is not installed")
def test_tesseract_real_fixture_fake():
    fixture_path = FIXTURES_DIR / "profile_fake.png"
    assert fixture_path.exists(), "profile_fake.png fixture is missing"

    with open(fixture_path, "rb") as f:
        img_bytes = f.read()

    res = extract_from_screenshot(img_bytes)
    assert res["backend_used"] == "tesseract"
    parsed = res["parsed"]

    # Exact expected values:
    # username user12fake45, 0 posts, 5 followers, 3000 following, full name "User", default grey picture, public
    assert parsed["username"] == "user12fake45"
    assert parsed["posts"] == 0
    assert parsed["followers"] == 5
    assert parsed["following"] == 3000
    assert "User" in (parsed["full_name"] or "")
    assert parsed["has_custom_profile_picture"] is False
    assert parsed["is_private"] is False


# 3. Noise / Random Image Tests: Return Nulls, Never Zeros

@pytest.mark.skipif(pytesseract is None, reason="Tesseract OCR is not installed")
def test_noise_image_returns_nulls_not_zeros():
    # Pure white image with no text
    img = Image.new("RGB", (200, 200), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    res = extract_from_screenshot(buf.getvalue())
    parsed = res["parsed"]
    assert parsed["username"] is None
    assert parsed["posts"] is None
    assert parsed["followers"] is None
    assert parsed["following"] is None
    assert res["confidence"]["posts"] == "none"
    assert res["confidence"]["followers"] == "none"
    assert res["confidence"]["following"] == "none"


# 4. Memory-Only Safety Test: No Files Created on Disk

def test_screenshot_processing_memory_only(tmp_path):
    # Snapshot directory before extraction
    before_files = set(Path(".").rglob("*.png")) | set(Path(".").rglob("*.jpg"))

    fixture_path = FIXTURES_DIR / "profile_genuine.png"
    with open(fixture_path, "rb") as f:
        img_bytes = f.read()

    res = extract_from_screenshot(img_bytes)
    assert res is not None

    after_files = set(Path(".").rglob("*.png")) | set(Path(".").rglob("*.jpg"))
    # No new image files were written to disk
    assert before_files == after_files


# 5. Optional Live Claude Test (Skipped if ANTHROPIC_API_KEY is not set)

@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="No live ANTHROPIC_API_KEY set in environment")
def test_live_claude_vision_extraction():
    # Live test on real fixtures
    api_key = os.getenv("ANTHROPIC_API_KEY")
    with open(FIXTURES_DIR / "profile_genuine.png", "rb") as f:
        gen_bytes = f.read()
    gen_data = extract_data_via_claude(gen_bytes, api_key=api_key)
    assert gen_data["username"] == "srajankulal27"
    assert gen_data["posts"] == 120
    assert gen_data["followers"] == 800

    with open(FIXTURES_DIR / "profile_fake.png", "rb") as f:
        fake_bytes = f.read()
    fake_data = extract_data_via_claude(fake_bytes, api_key=api_key)
    assert fake_data["username"] == "user12fake45"
    assert fake_data["posts"] == 0
    assert fake_data["followers"] == 5
