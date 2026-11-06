"""Unit tests for data cleaning and preprocessing functions in src/preprocessing.py.
"""
import pytest
import pandas as pd
import numpy as np

from src.preprocessing import (
    remove_duplicates,
    fix_dtypes,
    flag_impossible_values,
    handle_missing_values,
    clean_and_split_data,
)


@pytest.fixture
def sample_raw_df() -> pd.DataFrame:
    """Provides a synthetic test DataFrame with duplicates, bad types, negatives, and NaNs."""
    return pd.DataFrame({
        "profile pic": [1, 1, 1, 0, 1],
        "nums/length username": [0.1, 0.2, 0.1, 0.5, 0.1],
        "fullname words": [2, 1, 2, 0, 2],
        "nums/length fullname": [0.0, 0.0, 0.0, 0.2, 0.0],
        "name==username": [0, 0, 0, 1, 0],
        "description length": [45, 0, 45, 12, 45],
        "external URL": [0, 1, 0, 0, 0],
        "private": [0, 0, 0, 1, 0],
        "#posts": [100, 20, 100, 5, 100],
        "#followers": [1500, 300, 1500, 50, 1500],
        "#follows": [400, 150, 400, 200, 400],
        "fake": [0, 1, 0, 1, 0]
    })


def test_remove_duplicates(sample_raw_df):
    # Rows index 0, 2, 4 are identical duplicates
    cleaned = remove_duplicates(sample_raw_df)
    assert len(cleaned) == 3
    assert cleaned.duplicated().sum() == 0


def test_fix_dtypes():
    df = pd.DataFrame({
        "#posts": ["10", "25", "invalid"],
        "ratio": ["0.45", "0.80", "1.0"],
        "category": ["A", "B", "C"]
    })
    fixed = fix_dtypes(df, numeric_cols=["#posts", "ratio"])
    assert pd.api.types.is_numeric_dtype(fixed["#posts"])
    assert pd.api.types.is_numeric_dtype(fixed["ratio"])
    assert np.isnan(fixed.loc[2, "#posts"])


def test_flag_impossible_values():
    df = pd.DataFrame({
        "#posts": [10, -5, 20],
        "#followers": [-100, 50, 200],
        "unrelated": [-1, -2, -3]
    })
    flagged = flag_impossible_values(df, count_columns=["#posts", "#followers"])
    assert np.isnan(flagged.loc[1, "#posts"])
    assert np.isnan(flagged.loc[0, "#followers"])
    # unrelated should be untouched
    assert flagged.loc[0, "unrelated"] == -1


def test_handle_missing_values_no_leakage():
    train_df = pd.DataFrame({
        "feature_num": [10.0, 20.0, np.nan, 30.0],
        "feature_cat": ["A", "B", "A", np.nan],
        "fake": [0, 1, 0, 1]
    })
    test_df = pd.DataFrame({
        "feature_num": [np.nan, 100.0],
        "feature_cat": [np.nan, "B"],
        "fake": [0, 1]
    })

    train_imputed, test_imputed, stats = handle_missing_values(
        train_df, test_df, target_col="fake"
    )

    # Median of [10.0, 20.0, 30.0] is 20.0
    assert stats["feature_num"] == 20.0
    assert train_imputed.loc[2, "feature_num"] == 20.0
    # Test set missing value imputed using train median (20.0), not test distribution
    assert test_imputed.loc[0, "feature_num"] == 20.0

    # Mode of ['A', 'B', 'A'] is 'A'
    assert stats["feature_cat"] == "A"
    assert train_imputed.loc[3, "feature_cat"] == "A"
    assert test_imputed.loc[0, "feature_cat"] == "A"


def test_clean_and_split_data_proportions():
    # 20 samples: 10 fake, 10 genuine
    df = pd.DataFrame({
        "feature": list(range(20)),
        "#followers": [10] * 20,
        "fake": [0] * 10 + [1] * 10
    })
    train_df, test_df = clean_and_split_data(
        df, target_col="fake", test_size=0.2, random_state=42
    )

    assert len(train_df) == 16
    assert len(test_df) == 4
    # Check exact stratification
    assert (train_df["fake"] == 0).sum() == 8
    assert (train_df["fake"] == 1).sum() == 8
    assert (test_df["fake"] == 0).sum() == 2
    assert (test_df["fake"] == 1).sum() == 2

