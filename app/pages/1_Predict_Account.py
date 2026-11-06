import streamlit as st
import pandas as pd
from src.predict import Predictor
from src.database import log_prediction

st.set_page_config(page_title="Single Account Prediction", page_icon="🔍", layout="wide")
st.title("🔍 Single Account Risk Assessment")

st.markdown("Enter profile attributes to evaluate whether an account exhibits authentic or fake/spammer behavior.")

try:
    predictor = Predictor()
except Exception as e:
    st.error(f"Failed to load prediction pipeline: {e}")
    st.stop()

with st.form("manual_account_form"):
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Profile Basics")
        has_pic = st.selectbox("Profile Picture Present?", [1, 0], format_func=lambda x: "Yes" if x == 1 else "No")
        username_digit_ratio = st.number_input("Username Digit Ratio (nums/length username)", min_value=0.0, max_value=1.0, value=0.05, step=0.01)
        fullname_words = st.number_input("Full Name Word Count", min_value=0, max_value=20, value=2, step=1)
        fullname_digit_ratio = st.number_input("Full Name Digit Ratio (nums/length fullname)", min_value=0.0, max_value=1.0, value=0.0, step=0.01)

    with col2:
        st.subheader("Account Metadata")
        name_equals_user = st.selectbox("Full Name Equals Username?", [0, 1], format_func=lambda x: "Yes" if x == 1 else "No")
        desc_length = st.number_input("Bio / Description Length (characters)", min_value=0, max_value=500, value=65, step=1)
        has_url = st.selectbox("External URL in Bio?", [0, 1], format_func=lambda x: "Yes" if x == 1 else "No")
        is_private = st.selectbox("Account Private?", [0, 1], format_func=lambda x: "Yes" if x == 1 else "No")

    with col3:
        st.subheader("Activity & Network")
        posts = st.number_input("Total Media Posts", min_value=0, value=150, step=1)
        followers = st.number_input("Follower Count", min_value=0, value=620, step=1)
        follows = st.number_input("Following Count", min_value=0, value=380, step=1)

    submitted = st.form_submit_button("Analyze Account", use_container_width=True)

if submitted:
    record = {
        "profile pic": int(has_pic),
        "nums/length username": float(username_digit_ratio),
        "fullname words": int(fullname_words),
        "nums/length fullname": float(fullname_digit_ratio),
        "name==username": int(name_equals_user),
        "description length": int(desc_length),
        "external URL": int(has_url),
        "private": int(is_private),
        "#posts": int(posts),
        "#followers": int(followers),
        "#follows": int(follows)
    }

    result = predictor.predict_record(record)
    log_prediction(
        mode="Manual Single",
        input_dict=record,
        label=result["label"],
        proba=result["fake_probability"],
        risk=result["risk_level"]
    )

    st.markdown("---")
    st.subheader("Audit Results")

    res_col1, res_col2, res_col3 = st.columns(3)
    with res_col1:
        if result["label"] == "Fake/Bot":
            st.error(f"### Classification: {result['label']}")
        else:
            st.success(f"### Classification: {result['label']}")

    with res_col2:
        st.metric("Fake Probability", f"{result['fake_probability'] * 100:.1f}%")
        st.progress(result["fake_probability"])

    with res_col3:
        risk_color = {
            "Low Risk": "green",
            "Needs Review": "orange",
            "High Risk": "red"
        }.get(result["risk_level"], "blue")
        st.markdown(f"### Risk Tier: :{risk_color}[{result['risk_level']}]")

    st.subheader("Top Contributing Features (Model Attention)")
    if result["top_features"]:
        imp_df = pd.DataFrame(result["top_features"])
        imp_df.columns = ["Feature", "Relative Importance"]
        st.dataframe(imp_df, use_container_width=True)

