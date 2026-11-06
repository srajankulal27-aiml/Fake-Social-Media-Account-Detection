import streamlit as st
import pandas as pd
from src.database import get_prediction_history

st.set_page_config(page_title="Prediction History", page_icon="📜", layout="wide")
st.title("📜 Prediction History & Audit Trail (v1.1)")

st.markdown("""
This page logs past single and batch inferences executed via the Streamlit interface, persisted in local SQLite storage.
""")

history_df = get_prediction_history(limit=100)

if not history_df.empty:
    st.dataframe(history_df, use_container_width=True)
    st.download_button(
        label="📥 Export History (CSV)",
        data=history_df.to_csv(index=False).encode("utf-8"),
        file_name="fsmd_prediction_history.csv",
        mime="text/csv"
    )
else:
    st.info("No prediction records logged in database yet. Try running an account prediction!")

