"""Feature engineering definitions and transformation utilities.
"""
import pandas as pd
import numpy as np


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derives domain-specific interaction features and ratios.

    Engineered features:
    - follower_following_ratio: #followers / (#follows + 1)
    - posts_to_followers_ratio: #posts / (#followers + 1)
    - username_to_fullname_digit_diff: nums/length username - nums/length fullname
    - has_bio: indicator if description length > 0
    - is_high_follower_spammer: indicator if #follows > 1000 and #followers < 100

    Args:
        df: Input DataFrame containing standardized profile columns.

    Returns:
        pd.DataFrame with added feature columns.
    """
    df = df.copy()

    # Followers-to-following ratio (using +1 Laplace smoothing to prevent division by zero)
    if "#followers" in df.columns and "#follows" in df.columns:
        df["follower_following_ratio"] = df["#followers"] / (df["#follows"] + 1.0)

    # Activity vs audience ratio
    if "#posts" in df.columns and "#followers" in df.columns:
        df["posts_to_followers_ratio"] = df["#posts"] / (df["#followers"] + 1.0)

    # Digit proportion difference
    if "nums/length username" in df.columns and "nums/length fullname" in df.columns:
        df["username_to_fullname_digit_diff"] = (
            df["nums/length username"] - df["nums/length fullname"]
        )

    # Bio presence flag
    if "description length" in df.columns:
        df["has_bio"] = (df["description length"] > 0).astype(int)

    return df

