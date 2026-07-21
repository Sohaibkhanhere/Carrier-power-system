"""Generate synthetic hourly KPI data to bridge the gap between last real data and today.

Uses the real data's weekday/hour traffic shape per carrier, with calibrated
noise and day-to-day variation, so the synthetic fill looks plausible.
"""

from __future__ import annotations

import math
import random
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app import models


# --- Calibrated hourly shape per carrier type (weekday hours 0-23) ---
# Derived from real data analysis. Weekends are ~85-90% of weekday at peak.
WEEKDAY_SHAPE_1A = [
    66.2, 63.9, 57.9, 57.8, 48.1, 40.5, 34.0, 23.7,
    22.4, 23.6, 29.4, 47.2, 68.3, 72.2, 85.8, 89.3,
    87.9, 82.0, 58.7, 81.5, 78.9, 84.9, 83.5, 79.2,
]
WEEKDAY_SHAPE_1B = [
    54.3, 48.2, 42.0, 40.5, 33.1, 26.8, 22.0, 16.5,
    15.8, 16.2, 20.1, 33.5, 49.6, 55.8, 68.2, 71.4,
    69.3, 65.8, 42.5, 64.2, 62.0, 67.5, 66.1, 61.8,
]
WEEKDAY_SHAPE_1C = [
    58.0, 53.0, 46.8, 45.5, 37.0, 30.2, 25.0, 19.0,
    18.2, 19.0, 23.5, 38.0, 56.0, 62.5, 74.0, 77.5,
    75.5, 71.0, 47.0, 70.0, 67.5, 73.0, 71.5, 66.5,
]
WEEKDAY_SHAPE_2A = [
    65.5, 63.0, 57.0, 57.0, 47.5, 40.0, 33.5, 23.0,
    22.0, 23.0, 28.8, 46.5, 67.5, 71.5, 85.0, 88.5,
    87.0, 81.0, 58.0, 80.5, 78.0, 84.0, 82.5, 78.5,
]
WEEKDAY_SHAPE_2B = [
    46.0, 40.5, 35.0, 34.0, 27.5, 22.0, 18.0, 13.5,
    13.0, 13.2, 16.5, 27.5, 41.0, 46.5, 58.0, 61.0,
    59.5, 56.0, 36.0, 55.0, 53.0, 58.0, 56.5, 52.5,
]
WEEKDAY_SHAPE_2C = [
    45.5, 40.0, 34.5, 33.5, 27.0, 21.5, 17.8, 13.2,
    12.8, 13.0, 16.2, 27.0, 40.5, 46.0, 57.5, 60.5,
    59.0, 55.5, 35.5, 54.5, 52.5, 57.5, 56.0, 52.0,
]

WEEKEND_RATIO = {
    "1_A": 0.92, "1_B": 0.88, "1_C": 0.90,
    "2_A": 0.92, "2_B": 0.88, "2_C": 0.90,
}

WEEKDAY_SHAPES = {
    "1_A": WEEKDAY_SHAPE_1A, "1_B": WEEKDAY_SHAPE_1B, "1_C": WEEKDAY_SHAPE_1C,
    "2_A": WEEKDAY_SHAPE_2A, "2_B": WEEKDAY_SHAPE_2B, "2_C": WEEKDAY_SHAPE_2C,
}

# Traffic multiplier relative to PRB (approximate from real data)
TRAFFIC_SCALE = {
    "1_A": 1.6, "1_B": 1.2, "1_C": 1.3,
    "2_A": 1.6, "2_B": 1.1, "2_C": 1.1,
}

SECTOR_TO_TOWER_PREFIX = {"1_A": "Tower A", "1_B": "Tower A", "1_C": "Tower A",
                           "2_A": "Tower B", "2_B": "Tower B", "2_C": "Tower B"}


def _seed_for_date(d: date) -> float:
    """Deterministic per-day seed so the same date always produces the same shape."""
    return float(d.year * 10000 + d.month * 100 + d.day)


def generate_synthetic_row(sector: str, d: date, hour: int) -> tuple[float, float]:
    """Return (traffic_users, prb_utilization) for one carrier/date/hour."""
    shape = WEEKDAY_SHAPES[sector]
    base_prb = shape[hour]

    is_weekend = d.weekday() >= 5
    if is_weekend:
        base_prb *= WEEKEND_RATIO[sector]

    # Day-to-day slow drift (simulates weekly micro-trends)
    day_offset = (d - date(2026, 2, 15)).days
    drift = math.sin(day_offset * 0.15 + hash(sector) * 0.3) * 4.0

    # Deterministic noise from date+hour+sector
    rng = random.Random(_seed_for_date(d) * 100 + hour + hash(sector) % 97)
    noise = rng.gauss(0, 3.5)

    prb = max(2.0, min(99.0, base_prb + drift + noise))
    traffic = max(0.5, prb * TRAFFIC_SCALE[sector] * (0.85 + rng.random() * 0.3))

    return round(traffic, 4), round(prb, 4)


def generate_synthetic_gap(db: Session) -> int:
    """Fill every missing (carrier, date, hour) from the last real date up to now.

    For past days: generates all 24 hours.
    For today: generates only up to the current wall-clock hour.
    For future days: does nothing.

    Returns the number of rows inserted.
    """
    from datetime import datetime as dt

    # Find latest real date in DB
    max_date = db.query(func.max(models.KpiHourly.date)).scalar()
    if not max_date:
        return 0

    # Get all carriers
    carriers = db.query(models.Carrier).all()
    if not carriers:
        return 0

    now = dt.now()
    today = now.date()
    current_hour = now.hour

    # Nothing to do if we're already fully up to date
    if max_date > today:
        return 0

    count = 0

    # Fill past days (all 24 hours)
    if max_date < today:
        current = max_date + timedelta(days=1)
        while current < today:
            for carrier in carriers:
                for hour in range(24):
                    existing = (
                        db.query(models.KpiHourly)
                        .filter_by(carrier_id=carrier.id, date=current, hour=hour)
                        .first()
                    )
                    if not existing:
                        traffic, prb = generate_synthetic_row(
                            carrier.sector_label, current, hour
                        )
                        db.add(
                            models.KpiHourly(
                                carrier_id=carrier.id,
                                date=current,
                                hour=hour,
                                traffic_users=traffic,
                                prb_utilization=prb,
                                power_watts=0.0,
                                source="simulated_live",
                            )
                        )
                        count += 1
            current += timedelta(days=1)

    # Fill today up to the current hour (inclusive)
    for carrier in carriers:
        for hour in range(current_hour + 1):
            existing = (
                db.query(models.KpiHourly)
                .filter_by(carrier_id=carrier.id, date=today, hour=hour)
                .first()
            )
            if not existing:
                traffic, prb = generate_synthetic_row(
                    carrier.sector_label, today, hour
                )
                db.add(
                    models.KpiHourly(
                        carrier_id=carrier.id,
                        date=today,
                        hour=hour,
                        traffic_users=traffic,
                        prb_utilization=prb,
                        power_watts=0.0,
                        source="simulated_live",
                    )
                )
                count += 1

    db.flush()
    return count


def ensure_carrier_activation_orders(db: Session) -> int:
    """Backfill activation_order for any carriers that don't have one set yet.
    Returns number of carriers updated."""
    from sqlalchemy import or_
    carriers = (
        db.query(models.Carrier)
        .filter(or_(models.Carrier.activation_order == None, models.Carrier.activation_order == 0))
        .all()
    )
    count = 0
    for carrier in carriers:
        suffix = carrier.sector_label.split("_")[-1].upper()
        if len(suffix) == 1 and suffix.isalpha():
            carrier.activation_order = ord(suffix) - ord("A")
            count += 1
    db.flush()
    return count
