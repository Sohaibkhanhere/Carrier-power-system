from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.database import get_db
from app import models

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/towers")
def list_towers(db: Session = Depends(get_db)):
    """Return all towers from the database for dynamic filter population."""
    rows = (
        db.query(
            models.Tower.id,
            models.Tower.tower_label,
            models.Tower.site_id,
            func.count(models.Carrier.id).label("carrier_count"),
        )
        .join(models.Carrier, models.Carrier.tower_id == models.Tower.id, isouter=True)
        .group_by(models.Tower.id)
        .order_by(models.Tower.tower_label)
        .all()
    )
    return [
        {
            "id": r.id,
            "tower_label": r.tower_label,
            "site_id": r.site_id,
            "carrier_count": r.carrier_count,
        }
        for r in rows
    ]


@router.get("/kpi")
def list_kpi(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    tower: Optional[str] = None,
    carrier: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    source: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = (
        db.query(
            models.KpiHourly.id,
            models.Carrier.sector_label.label("carrier_sector"),
            models.Carrier.cell_name,
            models.Tower.tower_label,
            models.KpiHourly.date,
            models.KpiHourly.hour,
            models.KpiHourly.traffic_users,
            models.KpiHourly.prb_utilization,
            models.KpiHourly.power_watts,
            models.KpiHourly.source,
        )
        .join(models.Carrier, models.KpiHourly.carrier_id == models.Carrier.id)
        .join(models.Tower, models.Carrier.tower_id == models.Tower.id)
    )

    if tower:
        q = q.filter(models.Tower.tower_label == tower)
    if carrier:
        q = q.filter(models.Carrier.sector_label == carrier)
    if date_from:
        q = q.filter(models.KpiHourly.date >= date_from)
    if date_to:
        q = q.filter(models.KpiHourly.date <= date_to)
    if source:
        q = q.filter(models.KpiHourly.source == source)

    total = q.count()
    rows = (
        q.order_by(
            models.KpiHourly.date.desc(),
            models.KpiHourly.hour.desc(),
            models.Carrier.sector_label,
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [
            {
                "id": r.id,
                "carrier_sector": r.carrier_sector,
                "cell_name": r.cell_name,
                "tower_label": r.tower_label,
                "date": str(r.date),
                "hour": r.hour,
                "traffic_users": r.traffic_users,
                "prb_utilization": r.prb_utilization,
                "power_watts": round(r.power_watts, 2) if r.power_watts else 0,
                "source": r.source,
            }
            for r in rows
        ],
    }


@router.get("/summary")
def data_summary(db: Session = Depends(get_db)):
    total = db.query(func.count(models.KpiHourly.id)).scalar()
    carriers = db.query(func.count(models.Carrier.id)).scalar()
    sites = db.query(func.count(models.Site.id)).scalar()

    date_range = db.query(
        func.min(models.KpiHourly.date), func.max(models.KpiHourly.date)
    ).first()

    source_breakdown = (
        db.query(models.KpiHourly.source, func.count(models.KpiHourly.id))
        .group_by(models.KpiHourly.source)
        .all()
    )

    return {
        "total_kpi_rows": total,
        "total_carriers": carriers,
        "total_sites": sites,
        "date_range": {
            "from": str(date_range[0]) if date_range[0] else None,
            "to": str(date_range[1]) if date_range[1] else None,
        },
        "by_source": {src: cnt for src, cnt in source_breakdown},
    }


@router.get("/carriers")
def list_carriers(db: Session = Depends(get_db)):
    rows = (
        db.query(
            models.Carrier.id,
            models.Carrier.sector_label,
            models.Carrier.cell_name,
            models.Carrier.is_primary,
            models.Tower.tower_label,
        )
        .join(models.Tower, models.Carrier.tower_id == models.Tower.id)
        .order_by(models.Tower.tower_label, models.Carrier.sector_label)
        .all()
    )
    return [
        {
            "id": r.id,
            "sector_label": r.sector_label,
            "cell_name": r.cell_name,
            "is_primary": r.is_primary,
            "tower_label": r.tower_label,
        }
        for r in rows
    ]


@router.get("/today-vs-history")
def today_vs_history(
    carrier: str = Query(...),
    db: Session = Depends(get_db),
):
    """For today's weekday, return the historical average+range per hour vs today's actual."""
    from datetime import datetime as dt

    today = dt.now().date()
    dow = today.weekday()
    sqlite_dow = str((dow + 1) % 7)

    carrier_obj = (
        db.query(models.Carrier)
        .filter_by(sector_label=carrier)
        .first()
    )
    if not carrier_obj:
        return {"error": "Carrier not found"}

    # Historical same-weekday averages per hour
    historical = []
    for hour in range(24):
        rows = (
            db.query(models.KpiHourly)
            .filter(
                models.KpiHourly.carrier_id == carrier_obj.id,
                models.KpiHourly.hour == hour,
                models.KpiHourly.date != today,
                func.strftime("%w", models.KpiHourly.date) == sqlite_dow,
            )
            .all()
        )
        prb_vals = [r.prb_utilization for r in rows]
        if prb_vals:
            historical.append({
                "hour": hour,
                "avg": round(sum(prb_vals) / len(prb_vals), 2),
                "min": round(min(prb_vals), 2),
                "max": round(max(prb_vals), 2),
                "count": len(prb_vals),
            })
        else:
            historical.append({
                "hour": hour, "avg": 0, "min": 0, "max": 0, "count": 0,
            })

    # Today's actuals
    today_rows = (
        db.query(models.KpiHourly)
        .filter(
            models.KpiHourly.carrier_id == carrier_obj.id,
            models.KpiHourly.date == today,
        )
        .all()
    )
    today_actual = {r.hour: {"prb": r.prb_utilization, "traffic": r.traffic_users, "power": r.power_watts}
                    for r in today_rows}

    today_data = []
    for hour in range(24):
        if hour in today_actual:
            today_data.append({
                "hour": hour,
                "prb": round(today_actual[hour]["prb"], 2),
                "traffic": round(today_actual[hour]["traffic"], 2),
                "power": round(today_actual[hour]["power"], 2) if today_actual[hour]["power"] else 0,
            })

    return {
        "carrier": carrier,
        "date": str(today),
        "weekday": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dow],
        "historical": historical,
        "today": today_data,
    }


@router.get("/timeline")
def carrier_timeline(
    days: int = Query(7, ge=1, le=90),
    tower: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """ON/OFF decision timeline for carriers over the last N days."""
    from datetime import datetime as dt

    today = dt.now().date()
    start = today - timedelta(days=days)

    q = (
        db.query(
            models.Tower.tower_label,
            models.Carrier.sector_label,
            models.Carrier.id.label("carrier_id"),
            models.Decision.date,
            models.Decision.hour,
            models.Decision.mode,
            models.Decision.carrier_b_state,
            models.Decision.carrier_c_state,
        )
        .join(models.Tower, models.Decision.tower_id == models.Tower.id)
        .join(models.Carrier, models.Carrier.tower_id == models.Tower.id)
        .filter(models.Decision.date >= start, models.Decision.date <= today)
    )
    if tower:
        q = q.filter(models.Tower.tower_label == tower)

    rows = q.order_by(models.Decision.date, models.Decision.hour).all()

    pred_map = {}
    if rows:
        pred_q = (
            db.query(
                models.Prediction.carrier_id,
                models.Prediction.target_date,
                models.Prediction.target_hour,
                models.Prediction.predicted_prb,
            )
            .filter(
                models.Prediction.target_date >= start,
                models.Prediction.target_date <= today,
            )
        )
        for p in pred_q.all():
            pred_map[(p.carrier_id, str(p.target_date), p.target_hour)] = round(p.predicted_prb, 2) if p.predicted_prb is not None else None

    timeline = []
    for r in rows:
        sector = r.sector_label.split("_")[1].lower()
        if sector == "a":
            state = "ON"
        elif sector == "b":
            state = r.carrier_b_state
        else:
            state = r.carrier_c_state

        key = (r.carrier_id, str(r.date), r.hour)
        timeline.append({
            "tower": r.tower_label,
            "carrier": r.sector_label,
            "date": str(r.date),
            "hour": r.hour,
            "state": state,
            "mode": r.mode,
            "predicted_prb": pred_map.get(key),
        })

    return timeline


@router.get("/trend")
def actual_vs_predicted(
    carrier: str = Query(...),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
):
    """Actual vs predicted PRB for a carrier over a date range."""
    carrier_obj = (
        db.query(models.Carrier)
        .filter_by(sector_label=carrier)
        .first()
    )
    if not carrier_obj:
        return {"error": "Carrier not found"}

    q = (
        db.query(models.KpiHourly)
        .filter(models.KpiHourly.carrier_id == carrier_obj.id)
    )
    if date_from:
        q = q.filter(models.KpiHourly.date >= date_from)
    if date_to:
        q = q.filter(models.KpiHourly.date <= date_to)

    actual_rows = (
        q.order_by(models.KpiHourly.date, models.KpiHourly.hour)
        .all()
    )

    # Get predictions for the same range
    pq = (
        db.query(models.Prediction)
        .filter(models.Prediction.carrier_id == carrier_obj.id)
    )
    if date_from:
        pq = pq.filter(models.Prediction.target_date >= date_from)
    if date_to:
        pq = pq.filter(models.Prediction.target_date <= date_to)

    pred_rows = pq.order_by(models.Prediction.target_date, models.Prediction.target_hour).all()

    preds = {}
    for p in pred_rows:
        key = f"{p.target_date}_{p.target_hour}"
        preds[key] = p.predicted_prb

    data_points = []
    for r in actual_rows:
        key = f"{r.date}_{r.hour}"
        data_points.append({
            "date": str(r.date),
            "hour": r.hour,
            "actual_prb": round(r.prb_utilization, 2),
            "predicted_prb": round(preds.get(key, 0), 2) if key in preds else None,
            "actual_power": round(r.power_watts, 2) if r.power_watts else 0,
            "source": r.source,
        })

    return {
        "carrier": carrier,
        "tower_label": carrier_obj.tower.tower_label,
        "data": data_points,
    }


@router.get("/power-summary")
def power_summary(
    days: int = Query(7, ge=1, le=90),
    db: Session = Depends(get_db),
):
    """Power/energy summary: total power, savings, kWh per day."""
    from datetime import datetime as dt
    from app.services.power import get_power_config, compute_tower_power

    today = dt.now().date()
    from datetime import timedelta
    start = today - timedelta(days=days)

    pconfig = get_power_config(db)

    decisions = (
        db.query(models.Decision)
        .filter(models.Decision.date >= start, models.Decision.date <= today)
        .order_by(models.Decision.date, models.Decision.hour)
        .all()
    )

    all_on_power = compute_tower_power(True, True, True, 50, 50, 50, pconfig)

    daily = {}
    total_saved_wh = 0
    for d in decisions:
        day_str = str(d.date)
        if day_str not in daily:
            daily[day_str] = {"actual_wh": 0, "all_on_wh": 0, "hours": 0}
        daily[day_str]["actual_wh"] += d.power_watts
        daily[day_str]["all_on_wh"] += all_on_power
        daily[day_str]["hours"] += 1
        total_saved_wh += (all_on_power - d.power_watts)

    summary = []
    for day_str in sorted(daily.keys()):
        dd = daily[day_str]
        summary.append({
            "date": day_str,
            "actual_kwh": round(dd["actual_wh"] / 1000, 3),
            "baseline_kwh": round(dd["all_on_wh"] / 1000, 3),
            "saved_kwh": round((dd["all_on_wh"] - dd["actual_wh"]) / 1000, 3),
            "saved_pct": round((1 - dd["actual_wh"] / dd["all_on_wh"]) * 100, 1) if dd["all_on_wh"] > 0 else 0,
        })

    return {
        "total_saved_kwh": round(total_saved_wh / 1000, 3),
        "daily": summary,
    }
