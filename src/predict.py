"""Inference engine supporting single-record and batch predictions with SHAP explainability.
"""
from typing import Dict, Any, List, Union, Optional
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

        # Extract underlying classifier for feature importances and SHAP
        if hasattr(self.pipeline, "named_steps") and "classifier" in self.pipeline.named_steps:
            self.classifier = self.pipeline.named_steps["classifier"]
        else:
            self.classifier = self.pipeline

        # Initialize TreeExplainer for per-prediction explanations
        self.explainer = None
        try:
            import shap
            self.explainer = shap.TreeExplainer(self.classifier)
        except Exception as e:
            print(f"Warning: Failed to initialize TreeExplainer, will use fallback: {e}")
            self.explainer = None

    def get_global_contributions(self, top_n: int = 5, record_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Fallback returning top global feature importances labeled clearly as global."""
        if hasattr(self.classifier, "feature_importances_"):
            importances = self.classifier.feature_importances_
            feature_imp = sorted(
                zip(self.feature_names, importances),
                key=lambda x: x[1],
                reverse=True
            )
            results = []
            for f, imp in feature_imp[:top_n]:
                val = float(record_dict.get(f, 0.0)) if record_dict else 0.0
                results.append({
                    "feature": f,
                    "value": round(val, 4),
                    "contribution": round(float(imp), 4),
                    "direction": "Global Feature Importance",
                    "type": "global"
                })
            return results
        return []

    def compute_local_explanations(self, X_row: pd.DataFrame, top_n: int = 5) -> List[Dict[str, Any]]:
        """Computes local SHAP explanations for a single feature vector towards class 1 ('Fake').

        Returns top N features sorted by absolute contribution magnitude with signed value and direction.
        """
        if self.explainer is None:
            return self.get_global_contributions(top_n=top_n, record_dict=X_row.iloc[0].to_dict())

        try:
            # SHAP TreeExplainer calculation
            sv = self.explainer.shap_values(X_row)
            # In binary classification, sv may be an ndarray of shape (1, n_features, 2)
            # or a list of length 2 [class 0, class 1]
            if isinstance(sv, list) and len(sv) == 2:
                fake_sv = sv[1][0]
            elif isinstance(sv, np.ndarray) and sv.ndim == 3 and sv.shape[2] == 2:
                fake_sv = sv[0, :, 1]
            elif isinstance(sv, np.ndarray) and sv.ndim == 2:
                fake_sv = sv[0]
            else:
                fake_sv = sv[0]

            contributions = []
            row_dict = X_row.iloc[0].to_dict()
            for f_name, s_val in zip(self.feature_names, fake_sv):
                val = float(row_dict.get(f_name, 0.0))
                s_float = float(s_val)
                contributions.append({
                    "feature": f_name,
                    "value": round(val, 4),
                    "contribution": round(s_float, 4),
                    "direction": "Toward Fake" if s_float > 0 else "Toward Genuine",
                    "type": "local"
                })

            # Sort by absolute SHAP impact
            contributions.sort(key=lambda x: abs(x["contribution"]), reverse=True)
            return contributions[:top_n]
        except Exception as ex:
            print(f"SHAP explanation failed, falling back to global: {ex}")
            return self.get_global_contributions(top_n=top_n, record_dict=X_row.iloc[0].to_dict())

    def predict_record(self, record_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Runs inference and computes local SHAP feature contributions for a single profile."""
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

        # Compute per-prediction SHAP contributions
        top_features = self.compute_local_explanations(X, top_n=5)

        return {
            "prediction": prediction,
            "label": label,
            "fake_probability": round(proba, 4),
            "genuine_probability": round(1.0 - proba, 4),
            "risk_level": risk_level,
            "top_features": top_features
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
