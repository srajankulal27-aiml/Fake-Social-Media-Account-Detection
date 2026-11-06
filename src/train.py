"""Model training, 5-fold cross-validation, and selection module.
"""
from typing import Dict, Any, Tuple
import json
from pathlib import Path
import joblib
import pandas as pd
import numpy as np

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC

from src.config import RANDOM_STATE, CV_FOLDS, TARGET_COLUMN, MODELS_DIR, PROCESSED_DATA_DIR
from src.features import add_engineered_features


def get_candidate_models(random_state: int = RANDOM_STATE) -> Dict[str, Any]:
    """Define dictionary of candidate classification pipelines."""
    return {
        "Logistic Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(random_state=random_state, max_iter=1000))
        ]),
        "Decision Tree": Pipeline([
            ("classifier", DecisionTreeClassifier(random_state=random_state, max_depth=6))
        ]),
        "Random Forest": Pipeline([
            ("classifier", RandomForestClassifier(
                n_estimators=100, max_depth=8, random_state=random_state, n_jobs=-1
            ))
        ]),
        "KNN": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", KNeighborsClassifier(n_neighbors=5))
        ]),
        "SVM": Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", SVC(probability=True, random_state=random_state))
        ]),
    }


def evaluate_models_cv(
    X: pd.DataFrame,
    y: pd.Series,
    models: Dict[str, Any],
    cv_folds: int = CV_FOLDS,
    random_state: int = RANDOM_STATE
) -> pd.DataFrame:
    """Run stratified K-fold cross-validation across all models and return benchmark DataFrame."""
    skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)
    scoring = ["accuracy", "precision", "recall", "f1", "roc_auc"]
    
    records = []
    for name, pipeline in models.items():
        scores = cross_validate(pipeline, X, y, cv=skf, scoring=scoring, n_jobs=-1)
        records.append({
            "Model": name,
            "Accuracy": np.mean(scores["test_accuracy"]),
            "Precision": np.mean(scores["test_precision"]),
            "Recall": np.mean(scores["test_recall"]),
            "F1": np.mean(scores["test_f1"]),
            "ROC-AUC": np.mean(scores["test_roc_auc"]),
        })

    results_df = pd.DataFrame(records).sort_values(by=["Recall", "F1"], ascending=False).reset_index(drop=True)
    return results_df


def train_and_save_best_model() -> Tuple[str, pd.DataFrame]:
    """Train candidate models, select champion based on Recall and F1, fit on full train set, and serialize."""
    train_df = pd.read_csv(PROCESSED_DATA_DIR / "train.csv")
    train_df = add_engineered_features(train_df)

    feature_cols = [c for c in train_df.columns if c != TARGET_COLUMN]
    X_train = train_df[feature_cols]
    y_train = train_df[TARGET_COLUMN]

    models = get_candidate_models(random_state=RANDOM_STATE)
    cv_results = evaluate_models_cv(X_train, y_train, models)

    # Best model chosen by validation Recall and F1 (as specified in rule)
    best_model_name = cv_results.iloc[0]["Model"]
    best_pipeline = models[best_model_name]

    # Fit best model on the entire training set
    best_pipeline.fit(X_train, y_train)

    MODELS_DIR.mkdir(exist_ok=True)
    model_path = MODELS_DIR / "best_model.joblib"
    joblib.dump(best_pipeline, model_path)

    metadata = {
        "best_model_name": best_model_name,
        "features": feature_cols,
        "target": TARGET_COLUMN,
        "cv_results": cv_results.to_dict(orient="records"),
        "random_state": RANDOM_STATE,
        "train_samples": len(X_train)
    }
    with open(MODELS_DIR / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    return best_model_name, cv_results


if __name__ == "__main__":
    champion, summary = train_and_save_best_model()
    print(f"Champion Model Selected: {champion}\n")
    print(summary.to_string(index=False))

