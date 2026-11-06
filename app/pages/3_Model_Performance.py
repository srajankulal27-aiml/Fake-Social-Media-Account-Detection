import streamlit as st
import json
import pandas as pd
from PIL import Image
from src.config import MODELS_DIR, REPORTS_DIR

st.set_page_config(page_title="Model Performance", page_icon="📊", layout="wide")
st.title("📊 Model Evaluation & Benchmarks")

st.markdown("""
This dashboard displays the cross-validation benchmarks across candidate models, 
as well as the performance of the production pipeline on the untouched hold-out test set.
""")

metadata_path = MODELS_DIR / "metadata.json"
test_metrics_path = REPORTS_DIR / "test_evaluation_metrics.json"

if metadata_path.exists():
    with open(metadata_path, "r") as f:
        meta = json.load(f)

    st.subheader(f"🏆 Production Champion: {meta['best_model_name']}")

    cv_df = pd.DataFrame(meta["cv_results"])
    st.markdown("#### 5-Fold Stratified Cross-Validation Benchmark (Training Phase)")
    st.dataframe(
        cv_df.style.highlight_max(axis=0, subset=["Accuracy", "Precision", "Recall", "F1", "ROC-AUC"]),
        use_container_width=True
    )
else:
    st.warning("Model metadata not found. Please train models first.")

st.markdown("---")
st.subheader("🎯 Hold-Out Test Set Performance (20% Split)")

if test_metrics_path.exists():
    with open(test_metrics_path, "r") as f:
        test_m = json.load(f)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Accuracy", f"{test_m['accuracy']*100:.2f}%")
    c2.metric("Precision", f"{test_m['precision']*100:.2f}%")
    c3.metric("Recall", f"{test_m['recall']*100:.2f}%")
    c4.metric("F1-Score", f"{test_m['f1']*100:.2f}%")

    c5, c6 = st.columns(2)
    c5.metric("ROC-AUC Score", f"{test_m['roc_auc']:.4f}")
    c6.metric("PR-AUC Score", f"{test_m['pr_auc']:.4f}")

    st.markdown("#### Diagnostic Curves & Confusion Matrix")
    pcol1, pcol2 = st.columns(2)

    cm_img = REPORTS_DIR / "confusion_matrix.png"
    roc_img = REPORTS_DIR / "roc_pr_curves.png"

    if cm_img.exists():
        with pcol1:
            st.image(str(cm_img), caption="Test Confusion Matrix", use_column_width=True)

    if roc_img.exists():
        with pcol2:
            st.image(str(roc_img), caption="ROC & Precision-Recall Curves", use_column_width=True)
else:
    st.info("Test set evaluation metrics not yet generated.")

