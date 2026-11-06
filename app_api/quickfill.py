"""Quick Fill parsing and feature extraction utility for social media profiles.
Derives the 11 exact raw profile features without scraping or contacting external platforms.
"""
from typing import Dict, Any, Optional
import re


RESERVED_USERNAMES = {
    "p", "reel", "reels", "explore", "stories", "accounts", "direct",
    "tv", "tags", "channel", "login", "signup", "about", "developer"
}


def extract_username(url_or_handle: str) -> Optional[str]:
    """Extract and validate a social media username from a URL, handle, or string.
    Rejects reserved route words and invalid formats.
    Username must be 1-30 chars, alphanumeric or '.' or '_'.
    """
    if not url_or_handle:
        return None
    s = url_or_handle.strip()
    
    # Check if URL
    url_match = re.search(r"(?:https?://)?(?:www\.)?instagram\.com/([A-Za-z0-9._]+)", s, re.IGNORECASE)
    if url_match:
        candidate = url_match.group(1).rstrip("/")
    else:
        # Check if prefixed by @
        if s.startswith("@"):
            s = s[1:]
        # Extract first alphanumeric token if string has spaces
        parts = s.split()
        candidate = parts[0] if parts else ""

    candidate = candidate.strip()
    if not candidate:
        return None

    # Validate regex: 1 to 30 chars, letters, numbers, periods, underscores
    if not re.match(r"^[A-Za-z0-9._]{1,30}$", candidate):
        return None

    if candidate.lower() in RESERVED_USERNAMES:
        return None

    return candidate


def parse_metric_value(val_str: str) -> Optional[int]:
    """Parse number strings like '1,234', '1.2K', '3.5M', etc. into integer values.
    Handles common OCR character confusions:
    - O / o -> 0
    - l / I -> 1
    when adjacent to digits or decimal points.
    """
    if not val_str:
        return None
    cleaned = val_str.strip()
    
    # Replace commas and spaces
    cleaned = cleaned.replace(",", "").replace(" ", "")

    # OCR substitutions if mixed with numbers
    # If string contains digits or K/M, swap O/o to 0 and l/I to 1
    if re.search(r"\d", cleaned) or any(c in cleaned.lower() for c in ["k", "m"]):
        cleaned = re.sub(r"(?<=\d)[oO]|[oO](?=\d)", "0", cleaned)
        cleaned = re.sub(r"(?<=\d)[lI]|[lI](?=\d)", "1", cleaned)

    match = re.match(r"^(\d+(?:\.\d+)?)\s*([kKmMbB])?$", cleaned)
    if not match:
        return None

    num_part = float(match.group(1))
    multiplier_str = match.group(2)
    multiplier = 1.0

    if multiplier_str:
        m = multiplier_str.lower()
        if m == "k":
            multiplier = 1_000.0
        elif m == "m":
            multiplier = 1_000_000.0
        elif m == "b":
            multiplier = 1_000_000_000.0

    return int(round(num_part * multiplier))


def parse_counts(text: str) -> Dict[str, Optional[int]]:
    """Parse posts, followers, and following counts from raw text.
    Handles various orders and formats, e.g.:
    - '150 posts 1.2K followers 300 following'
    - '1,200 Followers, 350 Following, 42 Posts'
    - Multi-line blocks
    """
    results: Dict[str, Optional[int]] = {
        "posts": None,
        "followers": None,
        "following": None
    }
    if not text:
        return results

    # Normalize newlines and whitespace
    normalized = " " + text.replace("\n", " ").strip() + " "

    # Patterns for labeled counts: "<val> posts" or "posts: <val>"
    # Pattern 1: Number followed by label
    # e.g. "150 posts", "1.2M followers", "300 following"
    patterns_post_label = [
        ("posts", r"([\d.,]+[kKmMbB]?)\s*(?:posts?|publications?)\b"),
        ("followers", r"([\d.,]+[kKmMbB]?)\s*(?:followers?|abonn[eé]s?)\b"),
        ("following", r"([\d.,]+[kKmMbB]?)\s*(?:following|follows?|abonnements?)\b")
    ]

    for key, pat in patterns_post_label:
        m = re.search(pat, normalized, re.IGNORECASE)
        if m:
            val = parse_metric_value(m.group(1))
            if val is not None:
                results[key] = val

    # Pattern 2: Label followed by number
    # e.g. "posts: 150", "followers 1.2M", "following: 300"
    patterns_pre_label = [
        ("posts", r"\b(?:posts?|publications?)\s*[:\-]?\s*([\d.,]+[kKmMbB]?)"),
        ("followers", r"\b(?:followers?|abonn[eé]s?)\s*[:\-]?\s*([\d.,]+[kKmMbB]?)"),
        ("following", r"\b(?:following|follows?|abonnements?)\s*[:\-]?\s*([\d.,]+[kKmMbB]?)")
    ]

    for key, pat in patterns_pre_label:
        if results[key] is None:
            m = re.search(pat, normalized, re.IGNORECASE)
            if m:
                val = parse_metric_value(m.group(1))
                if val is not None:
                    results[key] = val

    return results


def compute_features(
    username: str,
    full_name: str = "",
    bio: str = "",
    posts: int = 0,
    followers: int = 0,
    following: int = 0,
    profile_pic: int = 1,
    is_private: int = 0
) -> Dict[str, Any]:
    """Compute the exact 11 raw features expected by the model pipeline,
    strictly matching training data definitions:
    - profile pic: 1 if user has photo, 0 otherwise
    - nums/length username: count of numeric digits / total username length (0.0 if empty)
    - fullname words: number of whitespace-separated tokens in fullname
    - nums/length fullname: count of numeric digits / total fullname length (0.0 if empty)
    - name==username: 1 if lowercase cleaned name equals lowercase cleaned username, else 0
    - description length: character length of bio
    - external URL: 1 if bio contains http:// or https:// or www. or .com/.org/.net/.io, else 0
    - private: 1 if private, 0 otherwise
    - #posts: int post count
    - #followers: int follower count
    - #follows: int following count
    """
    clean_username = (username or "").strip()
    clean_fullname = (full_name or "").strip()
    clean_bio = (bio or "").strip()

    # nums/length username
    u_len = len(clean_username)
    u_digits = sum(1 for c in clean_username if c.isdigit())
    u_digit_ratio = round(u_digits / u_len, 4) if u_len > 0 else 0.0

    # fullname words
    fn_words = len(clean_fullname.split()) if clean_fullname else 0

    # nums/length fullname
    fn_len = len(clean_fullname)
    fn_digits = sum(1 for c in clean_fullname if c.isdigit())
    fn_digit_ratio = round(fn_digits / fn_len, 4) if fn_len > 0 else 0.0

    # name==username
    # Strip spaces, underscores, and lowercase for comparison
    name_norm = clean_fullname.lower().replace(" ", "").replace("_", "").replace(".", "")
    user_norm = clean_username.lower().replace(" ", "").replace("_", "").replace(".", "")
    name_equals_user = 1 if (clean_username and name_norm == user_norm) else 0

    # description length
    desc_length = len(clean_bio)

    # external URL in bio
    url_pattern = r"(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9.\-]+\.(?:com|org|net|io|me|co|link|app)[^\s]*)"
    has_external_url = 1 if re.search(url_pattern, clean_bio, re.IGNORECASE) else 0

    return {
        "profile pic": int(profile_pic),
        "nums/length username": float(u_digit_ratio),
        "fullname words": int(fn_words),
        "nums/length fullname": float(fn_digit_ratio),
        "name==username": int(name_equals_user),
        "description length": int(desc_length),
        "external URL": int(has_external_url),
        "private": int(is_private),
        "#posts": int(max(0, posts)),
        "#followers": int(max(0, followers)),
        "#follows": int(max(0, following))
    }
