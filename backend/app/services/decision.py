"""Decision engine — capacity-based or threshold-based carrier management.

Selects between two algorithms based on the 'decision_logic' config field:
  - "capacity_based": activate minimum carriers so total_demand/n <= ceiling
  - "threshold_based": if ANY carrier exceeds the threshold, activate all carriers
"""

from __future__ import annotations

from datetime import date
from sqlalchemy.orm import Session

from app import models
from app.services.prediction import predict_prb
from app.services.power import (
    get_power_config, compute_tower_power, capacity_decide, threshold_decide,
)


def make_decisions_for_hour(target_date: date, hour: int, db: Session) -> list[dict]:
    """Evaluate all towers for a given date+hour using the configured decision logic."""
    pconfig = get_power_config(db)
    ceiling = pconfig["capacity_ceiling"]
    logic = pconfig.get("decision_logic", "capacity_based")
    threshold = pconfig.get("carrier_threshold", 70.0)
    towers = db.query(models.Tower).all()
    results = []

    for tower in towers:
        # Get carriers sorted by activation_order
        carriers = sorted(tower.carriers, key=lambda c: c.activation_order)

        # Build carrier load list for the capacity algorithm
        carrier_loads = []
        for carrier in carriers:
            pred = predict_prb(carrier.id, target_date, hour, db)
            carrier_loads.append({
                "sector_label": carrier.sector_label,
                "activation_order": carrier.activation_order,
                "predicted_prb": pred["predicted_prb"],
            })

        # Dispatch to the configured decision logic
        if logic == "threshold_based":
            decision_result = threshold_decide(carrier_loads, threshold)
        else:
            decision_result = capacity_decide(carrier_loads, ceiling)

        # Map carrier states back to B/C format for the decisions table
        carrier_states = {c["sector_label"]: c["is_on"] for c in decision_result["carriers"]}

        # Find B and C states (2nd and 3rd carriers by activation_order)
        sorted_sectors = [c.sector_label for c in sorted(carriers, key=lambda c: c.activation_order)]
        b_state = "ON" if len(sorted_sectors) > 1 and carrier_states.get(sorted_sectors[1], False) else "OFF"
        c_state = "ON" if len(sorted_sectors) > 2 and carrier_states.get(sorted_sectors[2], False) else "OFF"

        # Compute tower power
        prb_map = {c["sector_label"]: c["predicted_prb"] or 0 for c in carrier_loads}
        tower_power = compute_tower_power(
            True,  # A is always on
            b_state == "ON",
            c_state == "ON",
            prb_map.get(sorted_sectors[0], 0),
            prb_map.get(sorted_sectors[1], 0) if len(sorted_sectors) > 1 else 0,
            prb_map.get(sorted_sectors[2], 0) if len(sorted_sectors) > 2 else 0,
            pconfig,
        )

        # Average predicted PRB across all carriers for logging
        avg_prb = decision_result["per_carrier_load"]

        existing = (
            db.query(models.Decision)
            .filter_by(tower_id=tower.id, date=target_date, hour=hour)
            .first()
        )
        decision_record = {
            "tower_id": tower.id,
            "date": target_date,
            "hour": hour,
            "mode": decision_result["mode"],
            "carrier_b_state": b_state,
            "carrier_c_state": c_state,
            "predicted_prb_used": round(avg_prb, 2),
            "power_watts": tower_power,
            "total_demand": decision_result["total_demand"],
            "capacity_ceiling_used": ceiling,
            "active_count": decision_result["active_count"],
        }

        if existing:
            for k, v in decision_record.items():
                setattr(existing, k, v)
        else:
            db.add(models.Decision(**decision_record))

        results.append({
            "tower_label": tower.tower_label,
            "tower_id": tower.id,
            "mode": decision_result["mode"],
            "total_demand": decision_result["total_demand"],
            "capacity_ceiling": ceiling,
            "active_count": decision_result["active_count"],
            "per_carrier_load": decision_result["per_carrier_load"],
            "power_watts": tower_power,
            "carriers": decision_result["carriers"],
        })

    db.flush()
    return results


def make_decisions_for_date(target_date: date, db: Session) -> int:
    """Generate decisions for all 24 hours of a date. Returns count."""
    count = 0
    for hour in range(24):
        results = make_decisions_for_hour(target_date, hour, db)
        count += len(results)
    return count


def make_decisions_for_range(start: date, end: date, db: Session) -> int:
    """Generate decisions for a date range."""
    from datetime import timedelta
    count = 0
    current = start
    while current <= end:
        count += make_decisions_for_date(current, db)
        current += timedelta(days=1)
    return count
