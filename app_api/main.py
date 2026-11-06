"""FastAPI Web Application replacing Streamlit UI.
Serves REST API endpoints and Jinja2 Bootstrap 5 frontend pages.
"""
from contextlib import asynccontextmanager
from pathlib import Path
import json
import io
from typing import Dict, Any, List, Optional
from datetime import datetime

import pandas as pd
import numpy as np
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Query, status
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from src.config import BASE_DIR, REPORTS_DIR, MODELS_DIR, SAMPLE_DATA_DIR, PROCESSED_DATA_DIR
from src.predict import Predictor, assign_risk_tier
from src.database import log_prediction, get_prediction_history, clear_prediction_history
from app_api.schemas import (
    ProfilePredictRequest,
    PredictResponse,
    BatchPredictResponse,
    BatchSummary,
    HealthResponse,
)

# Global Predictor instance loaded once at startup
predictor_instance: Optional[Predictor] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model pipeline once on startup."""
    global predictor_instance
    try:
        predictor_instance = Predictor()
    except Exception as e:
        predictor_instance = None
        print(f"Warning: Failed to initialize Predictor during startup: {e}")
    yield
    # Cleanup if needed
    predictor_instance = None


app = FastAPI(
    title="Fake Social Media Detection API",
    description="Production REST API and Web Interface for detecting fake/bot social media profiles.",
    version="1.0.0",
    lifespan=lifespan
)

# Optional CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories & Mounts
STATIC_DIR = Path(__file__).resolve().parent / "static"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/reports-static", StaticFiles(directory=str(REPORTS_DIR)), name="reports-static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_predictor() -> Predictor:
    """Helper to ensure predictor is loaded."""
    global predictor_instance
    if predictor_instance is None:
        try:
            predictor_instance = Predictor()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Model pipeline not loaded or model artifact missing: {e}"
            )
    return predictor_instance


# ---------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint reporting API and model readiness."""
    meta_path = MODELS_DIR / "metadata.json"
    model_name = None
    target_col = None
    features_count = None

    if meta_path.exists():
        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)
                model_name = meta.get("best_model_name")
                target_col = meta.get("target")
                features_count = len(meta.get("features", []))
        except Exception:
            pass

    return HealthResponse(
        status="healthy",
        model_loaded=(predictor_instance is not None or (MODELS_DIR / "best_model.joblib").exists()),
        model_name=model_name,
        target_column=target_col,
        features_count=features_count
    )


@app.post("/api/predict", response_model=PredictResponse)
async def api_predict(payload: ProfilePredictRequest):
    """Predict fake/bot risk for a single account profile."""
    pred_engine = get_predictor()
    try:
        record_dict = payload.to_feature_dict()
        res = pred_engine.predict_record(record_dict)

        # Log into SQLite history
        log_prediction(
            mode="Single API",
            input_dict=record_dict,
            label=res["label"],
            proba=res["fake_probability"],
            risk=res["risk_level"]
        )

        return PredictResponse(
            label=res["label"],
            is_fake=res["prediction"],
            fake_probability=res["fake_probability"],
            genuine_probability=res["genuine_probability"],
            risk_level=res["risk_level"],
            top_features=res["top_features"],
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference processing error: {str(ex)}"
        )


@app.post("/api/predict-batch", response_model=BatchPredictResponse)
async def api_predict_batch(file: UploadFile = File(...)):
    """Upload CSV for batch account detection."""
    # 1. Extension check
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid file format. Only CSV files (.csv) are accepted."
        )

    # 2. Size check (Max 5 MB)
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded CSV file is empty."
        )
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum permitted limit of 5 MB."
        )

    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unable to parse CSV file: {str(ex)}"
        )

    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="CSV file contains headers but no data rows."
        )

    # 3. Column check
    required_cols = [
        "profile pic", "nums/length username", "fullname words",
        "nums/length fullname", "name==username", "description length",
        "external URL", "private", "#posts", "#followers", "#follows"
    ]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Uploaded CSV is missing mandatory columns: {missing_cols}"
        )

    # 4. Numeric type & negative values validation
    count_cols = ["fullname words", "description length", "#posts", "#followers", "#follows"]
    for col in required_cols:
        if not pd.api.types.is_numeric_dtype(df[col]):
            # Try to coerce
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if df[col].isnull().any():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Column '{col}' contains non-numeric invalid values."
                )

    for c in count_cols:
        if (df[c] < 0).any():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Column '{c}' contains impossible negative count values."
            )

    pred_engine = get_predictor()
    results_df = pred_engine.predict_batch(df)

    # Calculate summary
    total = len(results_df)
    fake_count = int((results_df["predicted_label"] == "Fake/Bot").sum())
    genuine_count = int((results_df["predicted_label"] == "Genuine").sum())
    low_risk = int((results_df["risk_level"] == "Low Risk").sum())
    review_risk = int((results_df["risk_level"] == "Needs Review").sum())
    high_risk = int((results_df["risk_level"] == "High Risk").sum())

    # Log summary to DB
    log_prediction(
        mode="Batch API",
        input_dict={"filename": file.filename, "rows": total},
        label=f"{fake_count} Fake / {genuine_count} Genuine",
        proba=float(results_df["fake_probability"].mean()),
        risk="Batch Audit"
    )

    records = results_df.to_dict(orient="records")

    return BatchPredictResponse(
        summary=BatchSummary(
            total_accounts=total,
            low_risk_count=low_risk,
            needs_review_count=review_risk,
            high_risk_count=high_risk,
            fake_count=fake_count,
            genuine_count=genuine_count
        ),
        predictions=records
    )


@app.get("/api/predict-batch/template")
async def download_batch_template():
    """Download template CSV for batch audits."""
    template_path = SAMPLE_DATA_DIR / "sample_batch_accounts.csv"
    if not template_path.exists():
        # Fallback create template if missing
        SAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        sample_df = pd.DataFrame([
            {
                "profile pic": 1,
                "nums/length username": 0.0,
                "fullname words": 2,
                "nums/length fullname": 0.0,
                "name==username": 0,
                "description length": 65,
                "external URL": 0,
                "private": 0,
                "#posts": 140,
                "#followers": 520,
                "#follows": 310
            },
            {
                "profile pic": 0,
                "nums/length username": 0.8,
                "fullname words": 0,
                "nums/length fullname": 0.0,
                "name==username": 1,
                "description length": 0,
                "external URL": 0,
                "private": 0,
                "#posts": 1,
                "#followers": 12,
                "#follows": 1800
            }
        ])
        sample_df.to_csv(template_path, index=False)

    return FileResponse(
        path=str(template_path),
        filename="sample_batch_accounts.csv",
        media_type="text/csv"
    )


@app.post("/api/predict-batch/download")
async def download_annotated_batch(file: UploadFile = File(...)):
    """Upload CSV and receive the annotated results CSV directly as a download."""
    batch_resp = await api_predict_batch(file)
    results_df = pd.DataFrame(batch_resp.predictions)
    
    stream = io.StringIO()
    results_df.to_csv(stream, index=False)
    stream.seek(0)

    return StreamingResponse(
        iter([stream.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=annotated_batch_predictions.csv"}
    )


@app.get("/api/history")
async def get_history(limit: int = Query(50, ge=1, le=200)):
    """Fetch past prediction history."""
    df = get_prediction_history(limit=limit)
    return df.to_dict(orient="records")


@app.delete("/api/history")
async def clear_history():
    """Clear past prediction logs."""
    deleted = clear_prediction_history()
    return {"status": "success", "rows_deleted": deleted}


@app.get("/api/metrics")
async def get_metrics():
    """Return model performance metrics and CV benchmarks."""
    metrics_path = REPORTS_DIR / "test_evaluation_metrics.json"
    meta_path = MODELS_DIR / "metadata.json"

    metrics_data = {}
    cv_data = []
    model_name = "Random Forest"

    if metrics_path.exists():
        with open(metrics_path, "r") as f:
            metrics_data = json.load(f)

    if meta_path.exists():
        with open(meta_path, "r") as f:
            meta = json.load(f)
            cv_data = meta.get("cv_results", [])
            model_name = meta.get("best_model_name", model_name)

    return {
        "model_name": model_name,
        "test_metrics": metrics_data,
        "cross_validation": cv_data
    }


@app.get("/api/eda-summary")
async def get_eda_summary():
    """Returns training class counts and descriptive statistics."""
    train_path = PROCESSED_DATA_DIR / "train.csv"
    if not train_path.exists():
        return JSONResponse(
            status_code=404,
            content={"detail": "Cleaned training data file not found."}
        )

    df = pd.read_csv(train_path)
    class_counts = df["fake"].value_counts().to_dict()
    desc = df.describe().T.reset_index().rename(columns={"index": "feature"})

    return {
        "total_train_rows": len(df),
        "class_counts": class_counts,
        "feature_statistics": desc.to_dict(orient="records")
    }


# ---------------------------------------------------------
# Frontend HTML Page Routes
# ---------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def page_home(request: Request):
    """Home landing page."""
    metrics_info = await get_metrics()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "model_name": metrics_info["model_name"],
            "metrics": metrics_info["test_metrics"]
        }
    )


@app.get("/predict", response_class=HTMLResponse)
async def page_predict(request: Request):
    """Single account prediction form page."""
    return templates.TemplateResponse(
        request=request,
        name="predict.html",
        context={}
    )


@app.get("/batch", response_class=HTMLResponse)
async def page_batch(request: Request):
    """Batch account detection page."""
    return templates.TemplateResponse(
        request=request,
        name="batch.html",
        context={}
    )


@app.get("/performance", response_class=HTMLResponse)
async def page_performance(request: Request):
    """Model performance and benchmarks page."""
    metrics_info = await get_metrics()
    return templates.TemplateResponse(
        request=request,
        name="performance.html",
        context={
            "model_name": metrics_info["model_name"],
            "metrics": metrics_info["test_metrics"],
            "cv_results": metrics_info["cross_validation"]
        }
    )


@app.get("/eda", response_class=HTMLResponse)
async def page_eda(request: Request):
    """Exploratory data analysis dashboard page."""
    eda_data = await get_eda_summary()
    stats = []
    if isinstance(eda_data, dict) and "feature_statistics" in eda_data:
        stats = eda_data["feature_statistics"]

    return templates.TemplateResponse(
        request=request,
        name="eda.html",
        context={
            "eda_stats": stats
        }
    )


@app.get("/history", response_class=HTMLResponse)
async def page_history(request: Request):
    """Prediction history log page."""
    history_records = await get_history(limit=50)
    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "history": history_records
        }
    )
