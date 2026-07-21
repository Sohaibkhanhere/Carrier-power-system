"""Seasonal/historical prediction engine with explainability.

For a given (carrier, date, hour), predict PRB utilization by averaging
the same weekday+hour from all available history. Returns the list of
contributing historical dates for full explainability.
"""

from __future__ import annotations

from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models


def _weekday_sql(d: date) -> str:
    """Convert Python weekday to SQLite %w format."""
    return str((d.weekday() + 1) % 7)


def predict_prb(
    carrier_id: int, target: date, target_hour: int, db: Session
) -> dict:
    """Return predicted PRB and range for one carrier at a given date+hour.

    Uses the average of all historical rows with the same weekday+hour.
    Includes full explainability: list of contributing historical dates.
    """
    sqlite_dow = _weekday_sql(target)

    rows = (
        db.query(models.KpiHourly)
        .filter(
            models.KpiHourly.carrier_id == carrier_id,
            models.KpiHourly.hour == target_hour,
            models.KpiHourly.date != target,
            func.strftime("%w", models.KpiHourly.date) == sqlite_dow,
        )
        .order_by(models.KpiHourly.date)
        .all()
    )

    if not rows:
        return {
            "predicted_prb": None,
            "predicted_traffic": None,
            "prb_min": None,
            "prb_max": None,
            "prb_std": None,
            "sample_count": 0,
            "contributing_dates": [],
            "limited_history": True,
        }

    prb_values = [r.prb_utilization for r in rows]
    traffic_values = [r.traffic_users for r in rows]
    n = len(prb_values)
    mean_prb = sum(prb_values) / n
    mean_traffic = sum(traffic_values) / n

    variance = sum((x - mean_prb) ** 2 for x in prb_values) / n if n > 1 else 0
    std_prb = variance**0.5

    # Build contributing dates list for explainability
    contributing = []
    for r in rows:
        contributing.append({
            "date": str(r.date),
            "weekday": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][r.date.weekday()],
            "traffic_users": round(r.traffic_users, 2),
            "prb_utilization": round(r.prb_utilization, 2),
            "power_watts": round(r.power_watts, 2) if r.power_watts else None,
            "source": r.source,
        })

    return {
        "predicted_prb": round(mean_prb, 2),
        "predicted_traffic": round(mean_traffic, 2),
        "prb_min": round(min(prb_values), 2),
        "prb_max": round(max(prb_values), 2),
        "prb_std": round(std_prb, 2),
        "sample_count": n,
        "contributing_dates": contributing,
        "limited_history": n < 4,
    }


def predict_carrier_range(
    carrier_id: int, target_date: date, db: Session
) -> list[dict]:
    """Predict all 24 hours for a carrier on a given date."""
    results = []
    for hour in range(24):
        pred = predict_prb(carrier_id, target_date, hour, db)
        results.append({"hour": hour, **pred})
    return results


def predict_all_carriers(target_date: date, db: Session, persist: bool = False) -> dict:
    """Predict all carriers for a given date (24 hours each).

    If persist=True, writes predictions to the predictions table for timeline/trend joins.
    """
    carriers = (
        db.query(models.Carrier)
        .join(models.Tower)
        .order_by(models.Tower.tower_label, models.Carrier.sector_label)
        .all()
    )
    result = {}
    for carrier in carriers:
        hourly = predict_carrier_range(carrier.id, target_date, db)
        result[carrier.sector_label] = {
            "carrier_id": carrier.id,
            "tower_label": carrier.tower.tower_label,
            "is_primary": carrier.is_primary,
            "hourly": hourly,
        }
        if persist:
            for h in hourly:
                existing = (
                    db.query(models.Prediction)
                    .filter_by(
                        carrier_id=carrier.id,
                        target_date=target_date,
                        target_hour=h["hour"],
                    )
                    .first()
                )
                if existing:
                    existing.predicted_prb = h["predicted_prb"]
                    existing.predicted_traffic = h["predicted_traffic"]
                else:
                    db.add(models.Prediction(
                        carrier_id=carrier.id,
                        target_date=target_date,
                        target_hour=h["hour"],
                        predicted_prb=h["predicted_prb"],
                        predicted_traffic=h["predicted_traffic"],
                    ))
    if persist:
        db.commit()
    return result


def predict_now(db: Session) -> dict:
    """Get current predictions for all carriers right now, using capacity-based decisions."""
    from datetime import datetime as dt

    now = dt.now()
    today = now.date()
    current_hour = now.hour

    carriers = (
        db.query(models.Carrier)
        .join(models.Tower)
        .order_by(models.Tower.tower_label, models.Carrier.activation_order)
        .all()
    )

    from app.services.power import get_power_config, compute_tower_power, capacity_decide
    pconfig = get_power_config(db)
    ceiling = pconfig["capacity_ceiling"]

    tower_results = {}
    for carrier in carriers:
        pred = predict_prb(carrier.id, today, current_hour, db)
        tower_label = carrier.tower.tower_label
        if tower_label not in tower_results:
            tower_results[tower_label] = {
                "tower_id": carrier.tower.id,
                "carriers": [],
                "tower_power_watts": 0,
                "total_demand": 0,
                "capacity_ceiling": ceiling,
                "active_count": 0,
                "mode": "unknown",
            }

        tower_results[tower_label]["carriers"].append({
            "sector_label": carrier.sector_label,
            "cell_name": carrier.cell_name,
            "is_primary": carrier.is_primary,
            "activation_order": carrier.activation_order,
            "current_hour": current_hour,
            "date": str(today),
            **pred,
            "is_on": False,  # will be set by capacity_decide below
        })

    # Run capacity-based decision for each tower
    for tower_label, tower_data in tower_results.items():
        carrier_loads = [
            {
                "sector_label": c["sector_label"],
                "activation_order": c["activation_order"],
                "predicted_prb": c["predicted_prb"],
            }
            for c in sorted(tower_data["carriers"], key=lambda x: x["activation_order"])
        ]
        dec = capacity_decide(carrier_loads, ceiling)

        # Update carrier ON/OFF states from decision result
        on_map = {c["sector_label"]: c["is_on"] for c in dec["carriers"]}
        for c in tower_data["carriers"]:
            c["is_on"] = on_map.get(c["sector_label"], False)

        tower_data["total_demand"] = dec["total_demand"]
        tower_data["active_count"] = dec["active_count"]
        tower_data["mode"] = dec["mode"]

        # Compute tower power
        sorted_carriers = sorted(tower_data["carriers"], key=lambda x: x["activation_order"])
        prbs = [c["predicted_prb"] or 0 for c in sorted_carriers]
        ons = [c["is_on"] for c in sorted_carriers]
        # Pad to 3 if fewer carriers
        while len(prbs) < 3:
            prbs.append(0)
            ons.append(False)
        tower_data["tower_power_watts"] = compute_tower_power(
            ons[0], ons[1], ons[2], prbs[0], prbs[1], prbs[2], pconfig
        )

    return {"date": str(today), "hour": current_hour, "towers": tower_results}
