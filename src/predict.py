"""Inference engine supporting single-record and batch predictions with risk-level stratification.
"""
from typing import Dict, Any, List, Union
import json
import joblib
import pandas as pd
import numpy as np

from src.config import MODELS_DIR
from src.features import add_engineered_features


def assign_risk_tier(probability: float) -> str:
    """Assigns risk tier based on predicted probability of being fake/bot.

    - Low Risk: prob < 0.35
    - Needs Review: 0.35 <= prob <= 0.70
    - High Risk: prob > 0.70
    """
    if probability < 0.35:
        return "Low Risk"
    elif probability <= 0.70:
        return "Needs Review"
    else:
        return "High Risk"


class Predictor:
    """Model predictor wrapper loading serialized pipeline artifact and metadata."""

    def __init__(self):
        model_path = MODELS_DIR / "best_model.joblib"
        metadata_path = MODELS_DIR / "metadata.json"
        if not model_path.exists() or not metadata_path.exists():
            raise FileNotFoundError("Model artifacts not found. Please run model training first.")

        self.pipeline = joblib.load(model_path)
        with open(metadata_path, "r") as f:
            self.metadata = json.load(f)

        self.feature_names = self.metadata["features"]

        # Extract underlying classifier for feature importances
        if hasattr(self.pipeline, "named_steps") and "classifier" in self.pipeline.named_steps:
            self.classifier = self.pipeline.named_steps["classifier"]
        else:
            self.classifier = self.pipeline

    def get_top_contributing_features(self, top_n: int = 4) -> List[Dict[str, Any]]:
        """Returns the top globally influential features according to the model."""
        if hasattr(self.classifier, "feature_importances_"):
            importances = self.classifier.feature_importances_
            feature_imp = sorted(
                zip(self.feature_names, importances),
                key=lambda x: x[1],
                reverse=True
            )
            return [{"feature": f, "importance": round(float(imp), 4)} for f, imp in feature_imp[:top_n]]
        return []

    def predict_record(self, record_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Runs inference on a single profile dictionary."""
        df = pd.DataFrame([record_dict])
        df_fe = add_engineered_features(df)

        # Ensure all model features exist
        for f in self.feature_names:
            if f not in df_fe.columns:
                df_fe[f] = 0

        X = df_fe[self.feature_names]
        proba = float(self.pipeline.predict_proba(X)[0, 1])
        prediction = int(proba >= 0.5)
        label = "Fake/Bot" if prediction == 1 else "Genuine"
        risk_level = assign_risk_tier(proba)

        return {
            "prediction": prediction,
            "label": label,
            "fake_probability": round(proba, 4),
            "genuine_probability": round(1.0 - proba, 4),
            "risk_level": risk_level,
            "top_features": self.get_top_contributing_features()
        }

    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Runs batch inference on an uploaded DataFrame and returns results."""
        df_in = df.copy()
        df_fe = add_engineered_features(df_in)

        # Validate and align features
        for f in self.feature_names:
            if f not in df_fe.columns:
                df_fe[f] = 0

        X = df_fe[self.feature_names]
        probas = self.pipeline.predict_proba(X)[:, 1]
        preds = (probas >= 0.5).astype(int)

        results_df = df.copy()
        results_df["predicted_label"] = np.where(preds == 1, "Fake/Bot", "Genuine")
        results_df["fake_probability"] = np.round(probas, 4)
        results_df["risk_level"] = [assign_risk_tier(p) for p in probas]

        return results_df

