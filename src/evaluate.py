"""Independent model evaluation module evaluating performance on the hold-out test set.
"""
import json
from pathlib import Path
import joblib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score, roc_auc_score,
    confusion_matrix, classification_report, roc_curve, precision_recall_curve, average_precision_score
)

from src.config import MODELS_DIR, PROCESSED_DATA_DIR, REPORTS_DIR, TARGET_COLUMN
from src.features import add_engineered_features


def evaluate_test_set():
    """Load hold-out test set and best model, compute test metrics, and generate evaluation plots."""
    model_path = MODELS_DIR / "best_model.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"Model artifact not found at {model_path}. Run src.train first.")

    pipeline = joblib.load(model_path)
    with open(MODELS_DIR / "metadata.json", "r") as f:
        metadata = json.load(f)

    test_df = pd.read_csv(PROCESSED_DATA_DIR / "test.csv")
    test_df = add_engineered_features(test_df)

    feature_cols = metadata["features"]
    X_test = test_df[feature_cols]
    y_test = test_df[TARGET_COLUMN]

    # Predictions
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    # Metrics
    test_metrics = {
        "model_name": metadata["best_model_name"],
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred)),
        "recall": float(recall_score(y_test, y_pred)),
        "f1": float(f1_score(y_test, y_pred)),
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
        "pr_auc": float(average_precision_score(y_test, y_proba)),
        "total_test_samples": int(len(y_test))
    }

    REPORTS_DIR.mkdir(exist_ok=True)
    with open(REPORTS_DIR / "test_evaluation_metrics.json", "w") as f:
        json.dump(test_metrics, f, indent=2)

    # 1. Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=["Genuine (0)", "Fake (1)"],
                yticklabels=["Genuine (0)", "Fake (1)"])
    plt.title(f"Test Confusion Matrix - {metadata['best_model_name']}")
    plt.xlabel("Predicted Label")
    plt.ylabel("True Label")
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "confusion_matrix.png", dpi=150)
    plt.close()

    # 2. ROC & PR Curves
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    precision_vals, recall_vals, _ = precision_recall_curve(y_test, y_proba)

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    # ROC Curve
    axes[0].plot(fpr, tpr, color="darkorange", lw=2, label=f"ROC (AUC = {test_metrics['roc_auc']:.3f})")
    axes[0].plot([0, 1], [0, 1], color="navy", lw=1, linestyle="--")
    axes[0].set_title("ROC Curve")
    axes[0].set_xlabel("False Positive Rate")
    axes[0].set_ylabel("True Positive Rate")
    axes[0].legend(loc="lower right")

    # PR Curve
    axes[1].plot(recall_vals, precision_vals, color="purple", lw=2, label=f"PR (AUC = {test_metrics['pr_auc']:.3f})")
    axes[1].set_title("Precision-Recall Curve")
    axes[1].set_xlabel("Recall")
    axes[1].set_ylabel("Precision")
    axes[1].legend(loc="lower left")

    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "roc_pr_curves.png", dpi=150)
    plt.close()

    return test_metrics, classification_report(y_test, y_pred)


if __name__ == "__main__":
    metrics, report = evaluate_test_set()
    print("Hold-out Test Metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")
    print("\nClassification Report:\n", report)

