"""ML-based prediction engine using scikit-learn (Random Forest).

Trains on historical KPI data with engineered features:
  - hour, day_of_week, is_weekend
  - rolling 24h average PRB
  - same-weekday lag (last N occurrences)
  - trend / week-index

Stores model artifacts via joblib, tracks MAE/RMSE per training run
in the model_runs table.
"""

from __future__ import annotations

import hashlib
import math
import os
from datetime import date, timedelta
from pathlib import Path

import joblib
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "models"


def _ensure_model_dir():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)


def _model_path(carrier_id: int) -> Path:
    _ensure_model_dir()
    return MODEL_DIR / f"rf_carrier_{carrier_id}.joblib"


def _model_version_path(carrier_id: int) -> Path:
    _ensure_model_dir()
    return MODEL_DIR / f"rf_carrier_{carrier_id}_version.txt"


def _build_features(carrier_id: int, target_date: date, target_hour: int, db: Session) -> dict | None:
    """Build feature vector for a single (carrier, date, hour) prediction."""
    from sqlalchemy import func as sqlfunc

    # Get all historical rows for this carrier, ordered by date+hour
    rows = (
        db.query(models.KpiHourly)
        .filter(models.KpiHourly.carrier_id == carrier_id)
        .order_by(models.KpiHourly.date, models.KpiHourly.hour)
        .all()
    )

    if len(rows) < 48:
        return None

    # Build a lookup for quick access
    lookup = {}
    for r in rows:
        lookup[(r.date, r.hour)] = r.prb_utilization

    # Current slot features
    hour = target_hour
    dow = target_date.weekday()
    is_weekend = 1 if dow >= 5 else 0

    # Rolling 24h average: average of previous 24 hours if available
    rolling_24h = []
    for h_off in range(1, 25):
        prev_hour = (target_hour - h_off) % 24
        prev_date = target_date - timedelta(days=1 if target_hour - h_off < 0 else 0)
        val = lookup.get((prev_date, prev_hour))
        if val is not None:
            rolling_24h.append(val)
    rolling_24h_avg = round(sum(rolling_24h) / len(rolling_24h), 2) if rolling_24h else None

    # Same-weekday lag: average of the same weekday+hour from previous weeks
    lag_values = []
    for weeks_back in range(1, 5):
        lag_date = target_date - timedelta(weeks=weeks_back)
        val = lookup.get((lag_date, target_hour))
        if val is not None:
            lag_values.append(val)
    same_weekday_lag = round(sum(lag_values) / len(lag_values), 2) if lag_values else None

    # Week index (weeks since first data point)
    first_date = rows[0].date
    week_index = max(0, (target_date - first_date).days // 7)

    return {
        "hour": hour,
        "day_of_week": dow,
        "is_weekend": is_weekend,
        "rolling_24h_avg": rolling_24h_avg,
        "same_weekday_lag": same_weekday_lag,
        "week_index": week_index,
    }


def _build_training_data(carrier_id: int, db: Session) -> tuple[list[list[float]], list[float], list[str]]:
    """Build training dataset: features + labels for all historical (date, hour) pairs.

    Returns (X, y, feature_names).
    """
    from sqlalchemy import func as sqlfunc

    rows = (
        db.query(models.KpiHourly)
        .filter(models.KpiHourly.carrier_id == carrier_id)
        .order_by(models.KpiHourly.date, models.KpiHourly.hour)
        .all()
    )

    if len(rows) < 48:
        return [], [], []

    lookup = {}
    all_dates_hours = []
    for r in rows:
        lookup[(r.date, r.hour)] = r.prb_utilization
        all_dates_hours.append((r.date, r.hour, r.prb_utilization))

    feature_names = ["hour", "day_of_week", "is_weekend", "rolling_24h_avg", "same_weekday_lag", "week_index"]
    first_date = all_dates_hours[0][0]

    X = []
    y = []

    for target_date, target_hour, prb_label in all_dates_hours:
        dow = target_date.weekday()
        is_weekend = 1 if dow >= 5 else 0

        # Rolling 24h
        rolling_24h = []
        for h_off in range(1, 25):
            prev_hour = (target_hour - h_off) % 24
            prev_date = target_date - timedelta(days=1 if target_hour - h_off < 0 else 0)
            val = lookup.get((prev_date, prev_hour))
            if val is not None:
                rolling_24h.append(val)
        rolling_24h_avg = sum(rolling_24h) / len(rolling_24h) if rolling_24h else 50.0

        # Same-weekday lag (exclude current row)
        lag_values = []
        for weeks_back in range(1, 5):
            lag_date = target_date - timedelta(weeks=weeks_back)
            val = lookup.get((lag_date, target_hour))
            if val is not None:
                lag_values.append(val)
        same_weekday_lag = sum(lag_values) / len(lag_values) if lag_values else 50.0

        week_index = max(0, (target_date - first_date).days // 7)

        X.append([target_hour, dow, is_weekend, rolling_24h_avg, same_weekday_lag, week_index])
        y.append(prb_label)

    return X, y, feature_names


def train_model(carrier_id: int, db: Session) -> dict:
    """Train a Random Forest regressor for one carrier.

    Returns training metrics and stores model to disk.
    """
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import cross_val_score
    from sklearn.metrics import mean_absolute_error, mean_squared_error

    X, y, feature_names = _build_training_data(carrier_id, db)

    if len(X) < 24:
        return {"error": f"Not enough data ({len(X)} rows). Need at least 24."}

    X_arr = np.array(X)
    y_arr = np.array(y)

    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=12,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_arr, y_arr)

    # Compute training metrics
    y_pred = model.predict(X_arr)
    mae = float(round(mean_absolute_error(y_arr, y_pred), 4))
    rmse = float(round(float(np.sqrt(mean_squared_error(y_arr, y_pred))), 4))

    # Cross-validation (5-fold)
    n_folds = min(5, len(X) // 6) if len(X) >= 30 else 2
    cv_scores = cross_val_score(model, X_arr, y_arr, cv=n_folds, scoring="neg_mean_absolute_error")
    cv_mae = float(round(-cv_scores.mean(), 4))

    # Feature importances
    importances = dict(zip(feature_names, [round(float(f), 4) for f in model.feature_importances_]))

    # Save model
    model_path = _model_path(carrier_id)
    joblib.dump(model, model_path)

    # Version = hash of training data for reproducibility
    data_hash = hashlib.md5(str(len(X)).encode() + y_arr.tobytes()[:1024]).hexdigest()[:8]
    version = f"rf_v1_{data_hash}"

    version_path = _model_version_path(carrier_id)
    version_path.write_text(version)

    # Log model run
    model_run = models.ModelRun(
        model_type="random_forest",
        training_row_count=len(X),
        mae=mae,
        rmse=rmse,
        notes=f"carrier_id={carrier_id} features={feature_names} cv_mae={cv_mae} importances={importances}",
    )
    db.add(model_run)
    db.commit()

    return {
        "carrier_id": carrier_id,
        "model_version": version,
        "training_rows": len(X),
        "features": feature_names,
        "mae": mae,
        "rmse": rmse,
        "cv_mae": cv_mae,
        "feature_importances": importances,
        "model_path": str(model_path),
    }


def predict_ml(carrier_id: int, target_date: date, target_hour: int, db: Session) -> dict | None:
    """Load the trained model and predict PRB for a single slot.

    Returns None if no model is available.
    """
    model_path = _model_path(carrier_id)
    if not model_path.exists():
        return None

    features = _build_features(carrier_id, target_date, target_hour, db)
    if features is None:
        return None

    model = joblib.load(model_path)
    X = np.array([[features["hour"], features["day_of_week"], features["is_weekend"],
                     features["rolling_24h_avg"], features["same_weekday_lag"], features["week_index"]]])

    pred = model.predict(X)[0]
    pred = max(0.0, min(100.0, float(round(pred, 2))))

    version_path = _model_version_path(carrier_id)
    version = version_path.read_text() if version_path.exists() else "unknown"

    return {
        "predicted_prb": pred,
        "model_version": version,
        "model_type": "random_forest",
        "features_used": features,
    }


def train_all_carriers(db: Session) -> list[dict]:
    """Train models for all carriers. Returns list of results."""
    carriers = db.query(models.Carrier).all()
    results = []
    for carrier in carriers:
        result = train_model(carrier.id, db)
        results.append(result)
    db.commit()
    return results


def predict_ml_bulk(carrier_id: int, date_from: date, date_to: date, db: Session) -> dict | None:
    """Load the trained model once and predict PRB for every hour in a date range.

    Returns a dict mapping "YYYY-MM-DD_HH" -> predicted_prb, or None if no model.
    """
    model_path = _model_path(carrier_id)
    if not model_path.exists():
        return None

    model = joblib.load(model_path)
    version_path = _model_version_path(carrier_id)
    version = version_path.read_text() if version_path.exists() else "unknown"

    results = {}
    current = date_from
    from datetime import timedelta
    while current <= date_to:
        for hour in range(24):
            features = _build_features(carrier_id, current, hour, db)
            if features is not None:
                X = np.array([[features["hour"], features["day_of_week"], features["is_weekend"],
                                 features["rolling_24h_avg"], features["same_weekday_lag"], features["week_index"]]])
                pred = model.predict(X)[0]
                pred = max(0.0, min(100.0, float(round(pred, 2))))
                results[f"{current}_{hour}"] = pred
        current += timedelta(days=1)

    return {"predictions": results, "model_version": version, "model_type": "random_forest"}


def get_model_runs(db: Session, limit: int = 50) -> list[dict]:
    """Get recent model training runs."""
    runs = (
        db.query(models.ModelRun)
        .order_by(models.ModelRun.trained_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "trained_at": r.trained_at.isoformat() if r.trained_at else None,
            "model_type": r.model_type,
            "training_row_count": r.training_row_count,
            "mae": r.mae,
            "rmse": r.rmse,
            "notes": r.notes,
        }
        for r in runs
    ]
