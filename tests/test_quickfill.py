"""Tests for Quick Fill parsing and feature derivation.
"""
import pytest
from app_api.quickfill import (
    extract_username,
    parse_metric_value,
    parse_counts,
    compute_features,
    RESERVED_USERNAMES
)


def test_extract_username_valid():
    assert extract_username("instagram.com/valid_user") == "valid_user"
    assert extract_username("https://www.instagram.com/john.doe/") == "john.doe"
    assert extract_username("@cool_user123") == "cool_user123"
    assert extract_username("plain_user") == "plain_user"


def test_extract_username_reserved_and_invalid():
    # Reserved words rejected
    assert extract_username("instagram.com/reels") is None
    assert extract_username("@explore") is None
    assert extract_username("https://instagram.com/p/") is None
    # Invalid characters rejected
    assert extract_username("bad!name?") is None
    assert extract_username("") is None


def test_parse_metric_value():
    assert parse_metric_value("150") == 150
    assert parse_metric_value("1,234") == 1234
    assert parse_metric_value("1.5K") == 1500
    assert parse_metric_value("3.2M") == 3200000
    # OCR substitutions (O -> 0, l -> 1)
    assert parse_metric_value("1O0") == 100
    assert parse_metric_value("l20") == 120
    assert parse_metric_value("invalid") is None


def test_parse_counts_text():
    sample_text = """
    @traveler_dan
    Dan Wilson
    150 posts  12.5K followers  340 following
    Digital Nomad
    """
    counts = parse_counts(sample_text)
    assert counts["posts"] == 150
    assert counts["followers"] == 12500
    assert counts["following"] == 340


def test_compute_features_exact_11():
    features = compute_features(
        username="bot_user_99",
        full_name="bot user 99",
        bio="Check out my links at https://freestuff.com",
        posts=5,
        followers=20,
        following=1500,
        profile_pic=0,
        is_private=0
    )
    # Check keys
    expected_keys = [
        "profile pic", "nums/length username", "fullname words",
        "nums/length fullname", "name==username", "description length",
        "external URL", "private", "#posts", "#followers", "#follows"
    ]
    for k in expected_keys:
        assert k in features

    assert features["profile pic"] == 0
    assert features["#posts"] == 5
    assert features["#followers"] == 20
    assert features["#follows"] == 1500
    assert features["external URL"] == 1
    assert features["nums/length username"] > 0
    assert features["name==username"] == 1

