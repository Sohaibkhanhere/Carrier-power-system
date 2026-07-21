"""ML model API endpoints — training, prediction, accuracy tracking."""

from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.services import ml_model, prediction

router = APIRouter(prefix="/api/ml", tags=["ml"])


@router.post("/train")
def train_all(db: Session = Depends(get_db)):
    """Train Random Forest models for all carriers."""
    results = ml_model.train_all_carriers(db)
    return {"trained": len(results), "results": results}


@router.post("/train/{carrier_id}")
def train_single(carrier_id: int, db: Session = Depends(get_db)):
    """Train a Random Forest model for a single carrier."""
    result = ml_model.train_model(carrier_id, db)
    return result


@router.get("/predict/{carrier_id}")
def ml_predict(
    carrier_id: int,
    target_date: date = Query(...),
    target_hour: int = Query(..., ge=0, le=23),
    db: Session = Depends(get_db),
):
    """Get ML prediction for a specific carrier/date/hour."""
    ml_result = ml_model.predict_ml(carrier_id, target_date, target_hour, db)
    if ml_result is None:
        return {"error": "No trained model available for this carrier. Train first."}
    return ml_result


@router.get("/compare/{carrier_id}")
def compare_models(
    carrier_id: int,
    target_date: date = Query(...),
    target_hour: int = Query(..., ge=0, le=23),
    db: Session = Depends(get_db),
):
    """Compare baseline (seasonal) vs ML prediction for a single slot."""
    baseline = prediction.predict_prb(carrier_id, target_date, target_hour, db)
    ml_result = ml_model.predict_ml(carrier_id, target_date, target_hour, db)

    carrier = db.query(models.Carrier).get(carrier_id)

    return {
        "carrier_id": carrier_id,
        "carrier_sector": carrier.sector_label if carrier else "unknown",
        "target_date": str(target_date),
        "target_hour": target_hour,
        "baseline": {
            "predicted_prb": baseline["predicted_prb"],
            "sample_count": baseline["sample_count"],
            "prb_std": baseline["prb_std"],
        },
        "ml": {
            "predicted_prb": ml_result["predicted_prb"] if ml_result else None,
            "model_version": ml_result["model_version"] if ml_result else None,
            "features_used": ml_result["features_used"] if ml_result else None,
        } if ml_result else None,
    }


@router.get("/runs")
def model_runs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get recent model training runs with accuracy metrics."""
    return ml_model.get_model_runs(db, limit)


@router.get("/accuracy-trend")
def accuracy_trend(db: Session = Depends(get_db)):
    """Get MAE/RMSE trend across all training runs for the accuracy chart."""
    runs = ml_model.get_model_runs(db, limit=200)

    trend = []
    for r in runs:
        if r["mae"] is not None:
            trend.append({
                "id": r["id"],
                "trained_at": r["trained_at"],
                "model_type": r["model_type"],
                "training_rows": r["training_row_count"],
                "mae": r["mae"],
                "rmse": r["rmse"],
            })

    return trend


@router.get("/status")
def ml_status(db: Session = Depends(get_db)):
    """Check which carriers have trained ML models."""
    carriers = db.query(models.Carrier).all()
    status = []
    for carrier in carriers:
        model_path = ml_model._model_path(carrier.id)
        version_path = ml_model._model_version_path(carrier.id)
        has_model = model_path.exists()
        version = version_path.read_text() if has_model and version_path.exists() else None
        status.append({
            "carrier_id": carrier.id,
            "sector_label": carrier.sector_label,
            "tower_label": carrier.tower.tower_label,
            "has_ml_model": has_model,
            "model_version": version,
        })
    return status


@router.get("/compare-range")
def compare_range(
    carrier_id: int,
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
):
    """Compare baseline vs ML predictions over a date range.

    Returns actual, baseline-predicted, and ML-predicted for each hour.
    """
    from datetime import timedelta

    carrier = db.query(models.Carrier).get(carrier_id)
    if not carrier:
        return {"error": "Carrier not found"}

    ml_bulk = ml_model.predict_ml_bulk(carrier_id, date_from, date_to, db)
    ml_predictions = ml_bulk["predictions"] if ml_bulk else {}

    results = []
    current = date_from
    while current <= date_to:
        for hour in range(24):
            actual_row = (
                db.query(models.KpiHourly)
                .filter_by(carrier_id=carrier_id, date=current, hour=hour)
                .first()
            )
            actual_prb = round(actual_row.prb_utilization, 2) if actual_row else None

            baseline = prediction.predict_prb(carrier_id, current, hour, db)

            key = f"{current}_{hour}"
            ml_prb = ml_predictions.get(key)

            results.append({
                "date": str(current),
                "hour": hour,
                "actual_prb": actual_prb,
                "baseline_prb": baseline["predicted_prb"],
                "ml_prb": ml_prb,
            })
        current += timedelta(days=1)

    return {
        "carrier_id": carrier_id,
        "carrier_sector": carrier.sector_label,
        "date_from": str(date_from),
        "date_to": str(date_to),
        "data": results,
    }
