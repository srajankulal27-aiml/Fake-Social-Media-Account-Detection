"""Unit and integration tests for model inference, schema validation, and reproducibility.
"""
import pytest
import pandas as pd
import numpy as np

from src.predict import Predictor, assign_risk_tier
from src.features import add_engineered_features


@pytest.fixture(scope="module")
def predictor():
    return Predictor()


def test_assign_risk_tier():
    assert assign_risk_tier(0.10) == "Low Risk"
    assert assign_risk_tier(0.34) == "Low Risk"
    assert assign_risk_tier(0.35) == "Needs Review"
    assert assign_risk_tier(0.60) == "Needs Review"
    assert assign_risk_tier(0.70) == "Needs Review"
    assert assign_risk_tier(0.71) == "High Risk"
    assert assign_risk_tier(0.99) == "High Risk"


def test_add_engineered_features():
    df = pd.DataFrame({
        "#followers": [100, 0],
        "#follows": [50, 10],
        "#posts": [20, 5],
        "nums/length username": [0.2, 0.5],
        "nums/length fullname": [0.0, 0.1],
        "description length": [40, 0]
    })
    res = add_engineered_features(df)
    assert "follower_following_ratio" in res.columns
    assert "posts_to_followers_ratio" in res.columns
    assert "username_to_fullname_digit_diff" in res.columns
    assert "has_bio" in res.columns
    assert res.loc[0, "has_bio"] == 1
    assert res.loc[1, "has_bio"] == 0


def test_predict_record_structure(predictor):
    sample = {
        "profile pic": 1,
        "nums/length username": 0.0,
        "fullname words": 2,
        "nums/length fullname": 0.0,
        "name==username": 0,
        "description length": 45,
        "external URL": 0,
        "private": 0,
        "#posts": 200,
        "#followers": 800,
        "#follows": 350
    }
    result = predictor.predict_record(sample)

    assert "prediction" in result
    assert "label" in result
    assert result["label"] in ["Genuine", "Fake/Bot"]
    assert 0.0 <= result["fake_probability"] <= 1.0
    assert result["risk_level"] in ["Low Risk", "Needs Review", "High Risk"]
    assert isinstance(result["top_features"], list)


def test_predict_batch(predictor):
    batch_df = pd.DataFrame([{
        "profile pic": 0,
        "nums/length username": 0.8,
        "fullname words": 0,
        "nums/length fullname": 0.0,
        "name==username": 1,
        "description length": 0,
        "external URL": 0,
        "private": 0,
        "#posts": 0,
        "#followers": 5,
        "#follows": 1500
    }, {
        "profile pic": 1,
        "nums/length username": 0.0,
        "fullname words": 2,
        "nums/length fullname": 0.0,
        "name==username": 0,
        "description length": 80,
        "external URL": 1,
        "private": 1,
        "#posts": 500,
        "#followers": 3000,
        "#follows": 400
    }])
    results = predictor.predict_batch(batch_df)

    assert len(results) == 2
    assert "predicted_label" in results.columns
    assert "fake_probability" in results.columns
    assert "risk_level" in results.columns


def test_reproducibility(predictor):
    sample = {
        "profile pic": 0,
        "nums/length username": 0.5,
        "fullname words": 1,
        "nums/length fullname": 0.0,
        "name==username": 0,
        "description length": 10,
        "external URL": 0,
        "private": 0,
        "#posts": 3,
        "#followers": 20,
        "#follows": 300
    }
    pred1 = predictor.predict_record(sample)
    pred2 = predictor.predict_record(sample)
    assert pred1["fake_probability"] == pred2["fake_probability"]
    assert pred1["label"] == pred2["label"]

