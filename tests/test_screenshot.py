"""Tests for screenshot parsing and in-memory image handling.
"""
import io
import pytest
from PIL import Image, ImageDraw
from app_api.screenshot import (
    preprocess_image_for_ocr,
    parse_profile_text_to_dict,
    extract_from_screenshot
)


def test_preprocess_image_for_ocr_memory_only():
    # Create simple in-memory test image
    img = Image.new("RGB", (200, 100), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Test Account", fill=(0, 0, 0))
    
    # Process without touching disk
    processed = preprocess_image_for_ocr(img)
    assert processed.mode == "L"
    assert processed.size[0] >= 200


def test_parse_profile_text_to_dict():
    text = (
        "@sample_user\n"
        "Jane Doe\n"
        "250 posts 1.8K followers 400 following\n"
        "Coffee lover and tech enthusiast\n"
        "Private Account\n"
    )
    res = parse_profile_text_to_dict(text)
    assert res["username"] == "sample_user"
    assert res["posts"] == 250
    assert res["followers"] == 1800
    assert res["following"] == 400
    assert res["is_private"] == 1


def test_extract_from_screenshot_graceful_handling():
    # Pass valid image bytes
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    result = extract_from_screenshot(img_bytes)
    assert isinstance(result, dict)
    assert "features" in result
    assert "profile pic" in result["features"]
    assert "error" in result

