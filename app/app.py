import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Fake Social Media Detection",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Fake Social Media Account Detection")
st.markdown("""
Welcome to the **Fake Social Media Account Detection** machine learning system. 

This platform evaluates social media account metadata (such as profile details, activity signals, and network ratios) to predict the likelihood that an account is **Genuine** or a **Fake/Bot**.

---
### 📌 System Features
- **🔍 1. Single Account Prediction:** Manually input profile features to get an immediate prediction, confidence probability, risk tier, and feature importances.
- **📂 2. Batch CSV Detection:** Upload CSV account rosters to run bulk detection, view stratified risk distributions, and download annotated audits.
- **📊 3. Model Performance:** Explore 5-fold cross-validation benchmarks across candidate models, confusion matrices, and ROC/PR evaluation curves.
- **📈 4. EDA Dashboard:** Inspect exploratory data analysis distributions, feature correlations, and class balance.
- **📜 5. Prediction History:** Review recent prediction audit trails stored locally.

---
### ⚠️ Operational Note
*Predictions are probabilistic estimates generated from trained machine learning models. Classification does not access private account information or perform live platform scraping.*
""")

st.info("👈 Use the sidebar navigation on the left to explore the application pages.")

