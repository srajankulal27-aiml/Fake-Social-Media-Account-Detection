"""FastAPI endpoint and integration test suite.
"""
import pytest
from pathlib import Path
import json
import pandas as pd
from fastapi.testclient import TestClient

from app_api.main import app
import src.database as db_module

# Test client
client = TestClient(app)


@pytest.fixture(autouse=True)
def override_test_db(tmp_path, monkeypatch):
    """Ensure database calls in test environment write to an isolated temporary SQLite db."""
    test_db = tmp_path / "test_predictions.db"
    monkeypatch.setattr(db_module, "DEFAULT_DB_PATH", test_db)
    monkeypatch.setattr("app_api.main.get_prediction_history", lambda limit=50: db_module.get_prediction_history(limit=limit, db_path=test_db))
    monkeypatch.setattr("app_api.main.clear_prediction_history", lambda: db_module.clear_prediction_history(db_path=test_db))
    monkeypatch.setattr("app_api.main.log_prediction", lambda mode, input_dict, label, proba, risk: db_module.log_prediction(mode, input_dict, label, proba, risk, db_path=test_db))


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["model_name"] == "Random Forest"


def test_predict_valid_payload():
    payload = {
        "profile pic": 1,
        "nums/length username": 0.0,
        "fullname words": 2,
        "nums/length fullname": 0.0,
        "name==username": 0,
        "description length": 45,
        "external URL": 0,
        "private": 0,
        "#posts": 150,
        "#followers": 500,
        "#follows": 300
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["label"] in ["Genuine", "Fake/Bot"]
    assert 0.0 <= data["fake_probability"] <= 1.0
    assert 0.0 <= data["genuine_probability"] <= 1.0
    assert abs((data["fake_probability"] + data["genuine_probability"]) - 1.0) < 0.01
    assert data["risk_level"] in ["Low Risk", "Needs Review", "High Risk"]
    assert len(data["top_features"]) > 0
    # Check that SHAP fields exist
    first_feat = data["top_features"][0]
    assert "feature" in first_feat
    assert "contribution" in first_feat
    assert "direction" in first_feat
    assert "value" in first_feat


def test_predict_different_accounts_different_explanations():
    """Verify that two different accounts produce distinct per-prediction local explanations."""
    genuine_payload = {
        "profile pic": 1,
        "nums/length username": 0.0,
        "fullname words": 2,
        "nums/length fullname": 0.0,
        "name==username": 0,
        "description length": 60,
        "external URL": 1,
        "private": 0,
        "#posts": 300,
        "#followers": 1500,
        "#follows": 400
    }
    fake_payload = {
        "profile pic": 0,
        "nums/length username": 0.85,
        "fullname words": 0,
        "nums/length fullname": 0.0,
        "name==username": 1,
        "description length": 0,
        "external URL": 0,
        "private": 0,
        "#posts": 0,
        "#followers": 5,
        "#follows": 2500
    }
    res_gen = client.post("/api/predict", json=genuine_payload).json()
    res_fake = client.post("/api/predict", json=fake_payload).json()

    exp_gen = res_gen["top_features"]
    exp_fake = res_fake["top_features"]

    assert len(exp_gen) > 0
    assert len(exp_fake) > 0

    # Ensure contributions are different across the two accounts
    gen_contribs = [(f["feature"], f["contribution"]) for f in exp_gen]
    fake_contribs = [(f["feature"], f["contribution"]) for f in exp_fake]
    assert gen_contribs != fake_contribs


def test_predict_negative_count_rejected():
    payload = {
        "profile pic": 1,
        "nums/length username": 0.0,
        "fullname words": 2,
        "nums/length fullname": 0.0,
        "name==username": 0,
        "description length": 45,
        "external URL": 0,
        "private": 0,
        "#posts": -10,  # Negative count should trigger validation error
        "#followers": 500,
        "#follows": 300
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422


def test_predict_missing_field_rejected():
    payload = {
        "profile pic": 1,
        "nums/length username": 0.0,
        # missing fullname words
        "nums/length fullname": 0.0,
        "name==username": 0,
        "description length": 45,
        "external URL": 0,
        "private": 0,
        "#posts": 100,
        "#followers": 500,
        "#follows": 300
    }
    response = client.post("/api/predict", json=payload)
    assert response.status_code == 422


def test_predict_batch_sample():
    sample_path = Path("data/sample/sample_batch_accounts.csv")
    assert sample_path.exists()

    with open(sample_path, "rb") as f:
        response = client.post(
            "/api/predict-batch",
            files={"file": ("sample_batch_accounts.csv", f, "text/csv")}
        )
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "predictions" in data
    assert data["summary"]["total_accounts"] == len(data["predictions"])
    assert data["summary"]["total_accounts"] > 0


def test_predict_batch_wrong_columns():
    csv_content = b"col_a,col_b\n1,2\n3,4"
    response = client.post(
        "/api/predict-batch",
        files={"file": ("invalid.csv", csv_content, "text/csv")}
    )
    assert response.status_code == 422
    assert "missing mandatory columns" in response.json()["detail"]


def test_predict_batch_empty_file():
    response = client.post(
        "/api/predict-batch",
        files={"file": ("empty.csv", b"", "text/csv")}
    )
    assert response.status_code == 422
    assert "empty" in response.json()["detail"].lower()


def test_history_flow():
    # Clear history first
    del_res = client.delete("/api/history")
    assert del_res.status_code == 200

    # Make a prediction
    payload = {
        "profile pic": 0,
        "nums/length username": 0.7,
        "fullname words": 0,
        "nums/length fullname": 0.0,
        "name==username": 1,
        "description length": 0,
        "external URL": 0,
        "private": 0,
        "#posts": 0,
        "#followers": 5,
        "#follows": 1200
    }
    client.post("/api/predict", json=payload)

    # Fetch history
    hist_res = client.get("/api/history")
    assert hist_res.status_code == 200
    history_list = hist_res.json()
    assert len(history_list) == 1
    assert history_list[0]["mode"] == "Single API"


@pytest.mark.parametrize("path", [
    "/",
    "/predict",
    "/batch",
    "/performance",
    "/eda",
    "/history"
])
def test_html_pages_return_200(path):
    response = client.get(path)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
