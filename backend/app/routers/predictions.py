"""Prediction, simulation, explainability, capacity config, and drill-down API endpoints."""

from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.services import prediction, synthetic, decision, power

router = APIRouter(prefix="/api", tags=["predictions"])


@router.post("/simulate/fill")
def fill_synthetic_data(db: Session = Depends(get_db)):
    count = synthetic.generate_synthetic_gap(db)
    db.commit()
    return {"rows_inserted": count}


@router.get("/live-status")
def live_status(db: Session = Depends(get_db)):
    return prediction.predict_now(db)


@router.get("/predictions/today")
def today_predictions(db: Session = Depends(get_db)):
    from datetime import datetime as dt
    return prediction.predict_all_carriers(dt.now().date(), db, persist=True)


@router.get("/predictions/date/{target_date}")
def predictions_for_date(target_date: date, db: Session = Depends(get_db)):
    return prediction.predict_all_carriers(target_date, db, persist=True)


@router.get("/predictions/explain")
def explain_prediction(
    carrier: str = Query(...),
    target_date: date = Query(...),
    target_hour: int = Query(...),
    db: Session = Depends(get_db),
):
    """Return the historical dates that contributed to a prediction,
    plus the capacity-based decision math for the carrier's tower."""
    from app import models
    carrier_obj = db.query(models.Carrier).filter_by(sector_label=carrier).first()
    if not carrier_obj:
        return {"error": "Carrier not found"}

    pred = prediction.predict_prb(carrier_obj.id, target_date, target_hour, db)
    weekday_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][target_date.weekday()]

    # Capacity-based decision math for the tower
    from app.services.power import get_power_config, capacity_decide
    pconfig = get_power_config(db)
    ceiling = pconfig["capacity_ceiling"]

    tower = carrier_obj.tower
    carriers = sorted(tower.carriers, key=lambda c: c.activation_order)
    carrier_loads = []
    for c in carriers:
        c_pred = prediction.predict_prb(c.id, target_date, target_hour, db)
        carrier_loads.append({
            "sector_label": c.sector_label,
            "activation_order": c.activation_order,
            "predicted_prb": c_pred["predicted_prb"],
        })

    cap_decision = capacity_decide(carrier_loads, ceiling)

    return {
        "carrier": carrier,
        "target_date": str(target_date),
        "target_hour": target_hour,
        "weekday": weekday_name,
        "predicted_prb": pred["predicted_prb"],
        "predicted_traffic": pred["predicted_traffic"],
        "prb_min": pred["prb_min"],
        "prb_max": pred["prb_max"],
        "prb_std": pred["prb_std"],
        "sample_count": pred["sample_count"],
        "limited_history": pred["limited_history"],
        "contributing_dates": pred["contributing_dates"],
        "capacity_decision": cap_decision,
        "capacity_ceiling": ceiling,
        "target_band_low": pconfig["target_band_low"],
        "target_band_high": pconfig["target_band_high"],
    }


@router.get("/month-position")
def month_position(
    carrier: str = Query(...),
    db: Session = Depends(get_db),
):
    """Compare early-month (1-15) vs late-month (16-31) same-weekday averages."""
    from app import models
    from datetime import datetime as dt

    carrier_obj = db.query(models.Carrier).filter_by(sector_label=carrier).first()
    if not carrier_obj:
        return {"error": "Carrier not found"}

    today = dt.now().date()
    dow = today.weekday()
    sqlite_dow = str((dow + 1) % 7)

    rows = (
        db.query(models.KpiHourly)
        .filter(
            models.KpiHourly.carrier_id == carrier_obj.id,
            models.KpiHourly.date != today,
            func.strftime("%w", models.KpiHourly.date) == sqlite_dow,
        )
        .all()
    )

    early = [(r.prb_utilization, r.traffic_users) for r in rows if r.date.day <= 15]
    late = [(r.prb_utilization, r.traffic_users) for r in rows if r.date.day > 15]

    def _stats(vals):
        if not vals:
            return {"avg_prb": 0, "avg_traffic": 0, "count": 0}
        prb = [v[0] for v in vals]
        trf = [v[1] for v in vals]
        return {
            "avg_prb": round(sum(prb) / len(prb), 2),
            "avg_traffic": round(sum(trf) / len(trf), 2),
            "count": len(prb),
        }

    early_stats = _stats(early)
    late_stats = _stats(late)

    diff = None
    if early_stats["avg_prb"] > 0 and late_stats["avg_prb"] > 0:
        diff = round(late_stats["avg_prb"] - early_stats["avg_prb"], 2)

    weekday_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dow]

    return {
        "carrier": carrier,
        "weekday": weekday_name,
        "early_month": early_stats,
        "late_month": late_stats,
        "difference_prb": diff,
        "note": _month_position_note(diff, weekday_name),
    }


def _month_position_note(diff, weekday_name):
    if diff is None:
        return "Not enough data for month-position analysis."
    direction = "higher" if diff > 0 else "lower"
    return f"Late-month {weekday_name}s run {abs(diff):.1f}% {direction} than early-month {weekday_name}s."


@router.get("/hour-drilldown")
def hour_drilldown(
    target_date: date = Query(...),
    target_hour: int = Query(...),
    db: Session = Depends(get_db),
):
    """Show every carrier's actual data + decision for a specific date+hour slot.

    Returns slot_status:
      - "available"  : data exists for this slot
      - "future"     : the requested date+hour hasn't occurred yet
      - "no_data"    : past/present but genuinely no data recorded
    """
    from datetime import datetime as dt
    from app import models

    now = dt.now()
    is_future = target_date > now.date() or (target_date == now.date() and target_hour > now.hour)

    rows = (
        db.query(
            models.Tower.id.label("tower_id"),
            models.Carrier.sector_label,
            models.Carrier.cell_name,
            models.Carrier.is_primary,
            models.Carrier.activation_order,
            models.Tower.tower_label,
            models.KpiHourly.traffic_users,
            models.KpiHourly.prb_utilization,
            models.KpiHourly.power_watts,
            models.KpiHourly.source,
        )
        .join(models.Carrier, models.KpiHourly.carrier_id == models.Carrier.id)
        .join(models.Tower, models.Carrier.tower_id == models.Tower.id)
        .filter(
            models.KpiHourly.date == target_date,
            models.KpiHourly.hour == target_hour,
        )
        .order_by(models.Tower.tower_label, models.Carrier.activation_order)
        .all()
    )

    # Future slot: no data should exist yet
    if is_future and not rows:
        return {
            "date": str(target_date),
            "hour": target_hour,
            "weekday": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][target_date.weekday()],
            "carriers": [],
            "slot_status": "future",
        }

    # No data in past/present: genuinely missing
    if not rows:
        return {
            "date": str(target_date),
            "hour": target_hour,
            "weekday": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][target_date.weekday()],
            "carriers": [],
            "slot_status": "no_data",
        }

    # Get decisions for this slot
    decisions = (
        db.query(models.Decision)
        .filter(models.Decision.date == target_date, models.Decision.hour == target_hour)
        .all()
    )
    dec_map = {d.tower_id: d for d in decisions}

    carriers = []
    for r in rows:
        carrier_data = {
            "carrier_sector": r.sector_label,
            "cell_name": r.cell_name,
            "is_primary": r.is_primary,
            "activation_order": r.activation_order,
            "tower_label": r.tower_label,
            "traffic_users": round(r.traffic_users, 2),
            "prb_utilization": round(r.prb_utilization, 2),
            "power_watts": round(r.power_watts, 2) if r.power_watts else 0,
            "source": r.source,
        }

        # Find matching decision
        dec = dec_map.get(r.tower_id)
        if dec:
            carrier_data["mode"] = dec.mode
            carrier_data["tower_power_watts"] = dec.power_watts
            carrier_data["total_demand"] = dec.total_demand
            carrier_data["capacity_ceiling_used"] = dec.capacity_ceiling_used
            carrier_data["active_count"] = dec.active_count

            # Determine ON/OFF from activation_order vs active_count
            sector = r.sector_label.split("_")[-1].upper()
            if r.is_primary or r.activation_order == 0:
                carrier_data["decision"] = "ON"
            elif r.activation_order == 1:
                carrier_data["decision"] = dec.carrier_b_state
            elif r.activation_order == 2:
                carrier_data["decision"] = dec.carrier_c_state
            else:
                carrier_data["decision"] = "ON" if r.activation_order < dec.active_count else "OFF"

        carriers.append(carrier_data)

    return {
        "date": str(target_date),
        "hour": target_hour,
        "weekday": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][target_date.weekday()],
        "carriers": carriers,
        "slot_status": "available",
    }


@router.post("/decisions/generate")
def generate_decisions_endpoint(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: Session = Depends(get_db),
):
    count = decision.make_decisions_for_range(date_from, date_to, db)
    db.commit()
    return {"decisions_created": count}


@router.get("/decisions/today")
def today_decisions(db: Session = Depends(get_db)):
    from datetime import datetime as dt
    today = dt.now().date()
    return _get_decisions(today, today, db)


@router.get("/decisions")
def list_decisions(
    date_from: date = Query(None),
    date_to: date = Query(None),
    tower: str = Query(None),
    db: Session = Depends(get_db),
):
    return _get_decisions(date_from, date_to, db, tower)


def _get_decisions(date_from, date_to, db, tower=None):
    from app import models
    q = (
        db.query(
            models.Decision.id,
            models.Tower.tower_label,
            models.Decision.date,
            models.Decision.hour,
            models.Decision.mode,
            models.Decision.carrier_b_state,
            models.Decision.carrier_c_state,
            models.Decision.predicted_prb_used,
            models.Decision.power_watts,
            models.Decision.total_demand,
            models.Decision.capacity_ceiling_used,
            models.Decision.active_count,
        )
        .join(models.Tower, models.Decision.tower_id == models.Tower.id)
    )
    if date_from:
        q = q.filter(models.Decision.date >= date_from)
    if date_to:
        q = q.filter(models.Decision.date <= date_to)
    if tower:
        q = q.filter(models.Tower.tower_label == tower)
    rows = q.order_by(models.Decision.date, models.Decision.hour, models.Tower.tower_label).all()

    return [
        {
            "id": r.id,
            "tower_label": r.tower_label,
            "date": str(r.date),
            "hour": r.hour,
            "mode": r.mode,
            "carrier_b_state": r.carrier_b_state,
            "carrier_c_state": r.carrier_c_state,
            "predicted_prb_used": r.predicted_prb_used,
            "power_watts": r.power_watts,
            "total_demand": r.total_demand,
            "capacity_ceiling_used": r.capacity_ceiling_used,
            "active_count": r.active_count,
        }
        for r in rows
    ]


# ─── Capacity-based config endpoints ───


@router.get("/capacity-config")
def get_capacity_config(db: Session = Depends(get_db)):
    return power.get_power_config(db)


@router.post("/capacity-config")
def set_capacity_config(body: dict, db: Session = Depends(get_db)):
    result = power.set_power_config(db, body)
    db.commit()
    return result


@router.get("/capacity-preview")
def capacity_preview(db: Session = Depends(get_db)):
    """Live preview: with current ceiling, how many carriers would be ON right now
    for each tower, given the slider's hypothetical ceiling."""
    from datetime import datetime as dt
    from app.services.prediction import predict_prb as predict_prb_fn
    from app.services.power import capacity_decide

    now = dt.now()
    today = now.date()
    current_hour = now.hour

    pconfig = power.get_power_config(db)
    ceiling = pconfig["capacity_ceiling"]

    towers = db.query(models.Tower).all()
    preview = {}
    for tower in towers:
        carriers = sorted(tower.carriers, key=lambda c: c.activation_order)
        carrier_loads = []
        for c in carriers:
            pred = predict_prb_fn(c.id, today, current_hour, db)
            carrier_loads.append({
                "sector_label": c.sector_label,
                "activation_order": c.activation_order,
                "predicted_prb": pred["predicted_prb"],
            })
        dec = capacity_decide(carrier_loads, ceiling)
        preview[tower.tower_label] = {
            "tower_id": tower.id,
            "total_demand": dec["total_demand"],
            "active_count": dec["active_count"],
            "max_carriers": dec["max_carriers"],
            "per_carrier_load": dec["per_carrier_load"],
            "mode": dec["mode"],
            "carriers": dec["carriers"],
        }
    return {"date": str(today), "hour": current_hour, "towers": preview}


@router.get("/test-scenario")
def test_scenario(
    load_a: float = Query(..., description="Hypothetical load for carrier A (%)"),
    load_b: float = Query(..., description="Hypothetical load for carrier B (%)"),
    load_c: float = Query(..., description="Hypothetical load for carrier C (%)"),
    ceiling: float = Query(None, description="Override ceiling (uses current config if omitted)"),
    db: Session = Depends(get_db),
):
    """Test scenario: given 3 hypothetical carrier loads,
    show how many carriers the configured algorithm would activate."""
    from app.services.power import capacity_decide, threshold_decide

    pconfig = power.get_power_config(db)
    logic = pconfig.get("decision_logic", "capacity_based")

    carrier_loads = [
        {"sector_label": "A", "activation_order": 0, "predicted_prb": load_a},
        {"sector_label": "B", "activation_order": 1, "predicted_prb": load_b},
        {"sector_label": "C", "activation_order": 2, "predicted_prb": load_c},
    ]

    if logic == "threshold_based":
        effective_threshold = pconfig.get("carrier_threshold", 70.0)
        result = threshold_decide(carrier_loads, effective_threshold)
        result["decision_logic"] = "threshold_based"
        result["carrier_threshold"] = effective_threshold
    else:
        effective_ceiling = ceiling if ceiling is not None else pconfig["capacity_ceiling"]
        result = capacity_decide(carrier_loads, effective_ceiling)
        result["decision_logic"] = "capacity_based"
        result["capacity_ceiling"] = effective_ceiling

    result["loads"] = {"A": load_a, "B": load_b, "C": load_c}
    return result


@router.get("/threshold")
def get_threshold(db: Session = Depends(get_db)):
    """Legacy endpoint - returns capacity_ceiling for backward compat."""
    pconfig = power.get_power_config(db)
    return {"threshold": pconfig["capacity_ceiling"]}


@router.post("/threshold")
def set_threshold(body: dict, db: Session = Depends(get_db)):
    """Legacy endpoint - sets capacity_ceiling for backward compat."""
    value = float(body.get("threshold", 80.0))
    power.set_power_config(db, {"capacity_ceiling": value})
    db.commit()
    return {"threshold": value}


# Legacy power-config endpoints (kept for backward compat)
@router.get("/power-config")
def get_power_config(db: Session = Depends(get_db)):
    return power.get_power_config(db)


@router.post("/power-config")
def set_power_config(body: dict, db: Session = Depends(get_db)):
    result = power.set_power_config(db, body)
    db.commit()
    return result
