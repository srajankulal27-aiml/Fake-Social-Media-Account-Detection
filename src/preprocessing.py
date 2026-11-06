"""Data cleaning, validation, and preprocessing routines.
"""
from typing import Tuple, List, Optional
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

from src.config import RANDOM_STATE, TEST_SIZE, TARGET_COLUMN


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate rows from DataFrame while preserving order."""
    return df.drop_duplicates().reset_index(drop=True)


def fix_dtypes(df: pd.DataFrame, numeric_cols: Optional[List[str]] = None) -> pd.DataFrame:
    """Ensure numeric columns are properly coerced to float/int and categorical to category/object.

    Args:
        df: Input DataFrame.
        numeric_cols: List of column names expected to be numeric. If None, coerses all existing
            numeric types explicitly.

    Returns:
        pd.DataFrame with corrected dtypes.
    """
    df = df.copy()
    if numeric_cols is None:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def flag_impossible_values(df: pd.DataFrame, count_columns: Optional[List[str]] = None) -> pd.DataFrame:
    """Flag or filter impossible values (such as negative follower/post counts or negative ratios).

    Negative count values are treated as invalid and replaced with NaN so downstream imputers
    can handle them systematically.

    Args:
        df: Input DataFrame.
        count_columns: Columns that strictly cannot be negative. If None, defaults to standard count fields.

    Returns:
        pd.DataFrame with negative values replaced by NaN.
    """
    df = df.copy()
    if count_columns is None:
        count_columns = [
            c for c in df.columns
            if any(term in c.lower() for term in ["posts", "followers", "follows", "words", "length"])
        ]

    for col in count_columns:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            mask = df[col] < 0
            if mask.any():
                df.loc[mask, col] = np.nan

    return df


def handle_missing_values(
    train_df: pd.DataFrame,
    test_df: Optional[pd.DataFrame] = None,
    target_col: Optional[str] = TARGET_COLUMN
) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], dict]:
    """Impute missing values using training statistics (median for numeric, mode for categorical).

    Prevents data leakage by fitting imputation values strictly on train_df and applying to test_df.

    Args:
        train_df: Training set.
        test_df: Optional test set to impute using train statistics.
        target_col: Column name of the target variable to exclude from imputation.

    Returns:
        Tuple of (clean_train_df, clean_test_df, imputation_values_dict).
    """
    train_clean = train_df.copy()
    test_clean = test_df.copy() if test_df is not None else None
    imputation_values = {}

    feature_cols = [c for c in train_clean.columns if c != target_col]

    for col in feature_cols:
        if pd.api.types.is_numeric_dtype(train_clean[col]):
            median_val = train_clean[col].median()
            # If all are NaN, default to 0
            median_val = 0 if pd.isna(median_val) else median_val
            imputation_values[col] = median_val
            train_clean[col] = train_clean[col].fillna(median_val)
            if test_clean is not None and col in test_clean.columns:
                test_clean[col] = test_clean[col].fillna(median_val)
        else:
            mode_series = train_clean[col].mode()
            mode_val = mode_series.iloc[0] if not mode_series.empty else "Unknown"
            imputation_values[col] = mode_val
            train_clean[col] = train_clean[col].fillna(mode_val)
            if test_clean is not None and col in test_clean.columns:
                test_clean[col] = test_clean[col].fillna(mode_val)

    return train_clean, test_clean, imputation_values


def clean_and_split_data(
    df: pd.DataFrame,
    target_col: str = TARGET_COLUMN,
    test_size: float = TEST_SIZE,
    random_state: int = RANDOM_STATE
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Full data cleaning and leak-free stratified train/test split.

    Pipeline:
    1. Remove duplicate rows.
    2. Enforce/fix dtypes.
    3. Flag and convert impossible negative values to NaN.
    4. Stratified 80/20 train/test split.
    5. Impute missing values fitted strictly on the train partition.

    Args:
        df: Raw combined DataFrame.
        target_col: Name of target column.
        test_size: Hold-out test fraction (default: 0.2).
        random_state: Random state seed for reproducibility.

    Returns:
        Tuple of (train_df, test_df).
    """
    df_cleaned = remove_duplicates(df)
    df_cleaned = fix_dtypes(df_cleaned)
    df_cleaned = flag_impossible_values(df_cleaned)

    # Stratified split before imputation to prevent data leakage
    train_df, test_df = train_test_split(
        df_cleaned,
        test_size=test_size,
        random_state=random_state,
        stratify=df_cleaned[target_col]
    )

    train_df = train_df.reset_index(drop=True)
    test_df = test_df.reset_index(drop=True)

    # Impute missing values using train statistics
    train_df, test_df, _ = handle_missing_values(train_df, test_df, target_col=target_col)

    return train_df, test_df

