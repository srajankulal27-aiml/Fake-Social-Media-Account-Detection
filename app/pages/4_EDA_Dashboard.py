import streamlit as st
import pandas as pd
from src.config import PROCESSED_DATA_DIR, REPORTS_DIR

st.set_page_config(page_title="EDA Dashboard", page_icon="📈", layout="wide")
st.title("📈 Exploratory Data Analysis (EDA)")

st.markdown("""
Visual summary of feature distributions, class separation, and dataset correlation properties.
""")

train_path = PROCESSED_DATA_DIR / "train.csv"

if train_path.exists():
    df = pd.read_csv(train_path)
    st.subheader("Training Dataset Preview")
    st.dataframe(df.head(10), use_container_width=True)

    st.markdown("---")
    st.subheader("Class Distribution & Correlations")

    col1, col2 = st.columns(2)
    dist_img = REPORTS_DIR / "eda_class_distribution.png"
    corr_img = REPORTS_DIR / "eda_correlation_matrix.png"

    if dist_img.exists():
        with col1:
            st.image(str(dist_img), caption="Class Balance (0 = Genuine, 1 = Fake)", use_column_width=True)

    if corr_img.exists():
        with col2:
            st.image(str(corr_img), caption="Feature Correlation Heatmap", use_column_width=True)

    st.markdown("---")
    st.subheader("Statistical Summary (Train Data)")
    st.dataframe(df.describe().T, use_container_width=True)
else:
    st.warning("Cleaned training data not found in data/processed/.")

