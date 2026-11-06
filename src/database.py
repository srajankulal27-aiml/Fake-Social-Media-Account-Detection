"""SQLite database logging module for persisting prediction history (v1.1).
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd
from src.config import BASE_DIR

DB_PATH = BASE_DIR / "predictions.db"


def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the prediction history schema if it does not already exist."""
    conn = get_connection()
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


def log_prediction(mode: str, input_dict: Dict[str, Any], label: str, proba: float, risk: str):
    """Logs a single or summary batch prediction into SQLite."""
    init_db()
    conn = get_connection()
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


def get_prediction_history(limit: int = 50) -> pd.DataFrame:
    """Retrieves recent prediction log records."""
    init_db()
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, timestamp, mode, predicted_label, fake_probability, risk_level FROM prediction_history ORDER BY id DESC LIMIT ?",
        conn,
        params=(limit,)
    )
    conn.close()
    return df

