"""Database utilities for logging prediction history and audits.
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import pandas as pd
from src.config import BASE_DIR

DEFAULT_DB_PATH = BASE_DIR / "predictions.db"


def get_connection(db_path: Optional[Path] = None):
    """Returns a connection to the SQLite database."""
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None):
    """Initializes the prediction history schema if it does not already exist."""
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prediction_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                mode TEXT NOT NULL,
                input_data TEXT NOT NULL,
                predicted_label TEXT NOT NULL,
                fake_probability REAL NOT NULL,
                risk_level TEXT NOT NULL
            )
        """)
    conn.close()


def log_prediction(
    mode: str,
    input_dict: Dict[str, Any],
    label: str,
    proba: float,
    risk: str,
    db_path: Optional[Path] = None
):
    """Logs a single or summary batch prediction into SQLite."""
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            INSERT INTO prediction_history (timestamp, mode, input_data, predicted_label, fake_probability, risk_level)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            mode,
            json.dumps(input_dict),
            label,
            float(proba),
            risk
        ))
    conn.close()


def get_prediction_history(limit: int = 50, db_path: Optional[Path] = None) -> pd.DataFrame:
    """Retrieves recent prediction log records."""
    init_db(db_path)
    conn = get_connection(db_path)
    df = pd.read_sql_query(
        "SELECT id, timestamp, mode, predicted_label, fake_probability, risk_level FROM prediction_history ORDER BY id DESC LIMIT ?",
        conn,
        params=(limit,)
    )
    conn.close()
    return df


def clear_prediction_history(db_path: Optional[Path] = None) -> int:
    """Clears all records from the prediction history table. Returns rows deleted."""
    init_db(db_path)
    conn = get_connection(db_path)
    with conn:
        cursor = conn.execute("DELETE FROM prediction_history")
        rows = cursor.rowcount
    conn.close()
    return rows
