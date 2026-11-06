import streamlit as st
import pandas as pd
from src.predict import Predictor
from src.config import SAMPLE_DATA_DIR
from src.database import log_prediction

st.set_page_config(page_title="Batch Account Detection", page_icon="📂", layout="wide")
st.title("📂 Batch Account Detection & Audit")

st.markdown("""
Upload a CSV file containing multiple social media profiles to run bulk detection.
The system validates the schema, computes predictions, categorizes risk levels, and generates an exportable audit report.
""")

try:
    predictor = Predictor()
except Exception as e:
    st.error(f"Failed to load predictor: {e}")
    st.stop()

# Sample data download option
sample_file = SAMPLE_DATA_DIR / "sample_batch_accounts.csv"
if sample_file.exists():
    with open(sample_file, "rb") as f:
        st.download_button(
            label="📥 Download Sample Batch CSV",
            data=f,
            file_name="sample_batch_accounts.csv",
            mime="text/csv"
        )

uploaded_file = st.file_uploader("Upload Account Roster (CSV)", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        st.write(f"**Loaded {len(df)} rows.** Preview:")
        st.dataframe(df.head(5), use_container_width=True)

        # Check required columns
        required_cols = [
            "profile pic", "nums/length username", "fullname words",
            "nums/length fullname", "name==username", "description length",
            "external URL", "private", "#posts", "#followers", "#follows"
        ]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            st.error(f"Uploaded CSV is missing mandatory columns: {missing}")
        else:
            if st.button("Run Batch Detection", type="primary"):
                with st.spinner("Processing batch predictions..."):
                    results_df = predictor.predict_batch(df)

                st.success("Batch classification completed!")

                # Summary metrics
                fake_count = (results_df["predicted_label"] == "Fake/Bot").sum()
                genuine_count = (results_df["predicted_label"] == "Genuine").sum()

                mcol1, mcol2, mcol3 = st.columns(3)
                mcol1.metric("Total Accounts", len(results_df))
                mcol2.metric("Flagged as Fake/Bot", f"{fake_count} ({fake_count/len(results_df)*100:.1f}%)")
                mcol3.metric("Genuine Accounts", f"{genuine_count} ({genuine_count/len(results_df)*100:.1f}%)")

                # Risk breakdown
                st.subheader("Risk Distribution")
                st.bar_chart(results_df["risk_level"].value_counts())

                # Table view
                st.subheader("Detailed Audit Roster")
                st.dataframe(results_df, use_container_width=True)

                # Export CSV
                csv_data = results_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download Annotated Audit CSV",
                    data=csv_data,
                    file_name="account_risk_audit_results.csv",
                    mime="text/csv",
                    type="primary"
                )

                # Log to DB
                log_prediction(
                    mode="CSV Batch",
                    input_dict={"total_rows": len(results_df), "fake_detected": int(fake_count)},
                    label=f"{fake_count} Fake / {genuine_count} Genuine",
                    proba=float(results_df["fake_probability"].mean()),
                    risk="Batch Audit"
                )

    except Exception as ex:
        st.error(f"Error parsing uploaded CSV: {ex}")

