"""Data loading utilities for ingesting raw datasets.
"""
from pathlib import Path
import pandas as pd
from src.config import RAW_DATA_DIR


def load_raw_csv(filename: str) -> pd.DataFrame:
    """Load a CSV file from the data/raw directory.

    Args:
        filename: Name of the CSV file (e.g. 'instagram_accounts.csv').

    Returns:
        pd.DataFrame: Loaded dataset.

    Raises:
        FileNotFoundError: If the file does not exist in data/raw.
        ValueError: If filename is empty or not a CSV.
    """
    if not filename or not filename.endswith(".csv"):
        raise ValueError(f"Invalid filename provided: '{filename}'. Must be a non-empty .csv file.")

    file_path = RAW_DATA_DIR / filename
    if not file_path.is_file():
        raise FileNotFoundError(
            f"Dataset not found at '{file_path}'. Please place the dataset CSV in '{RAW_DATA_DIR}'."
        )

    return pd.read_csv(file_path)

