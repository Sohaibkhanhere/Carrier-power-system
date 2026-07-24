"""Watt-based power model + capacity-based decision parameters.

Computes power_watts for a tower based on which carriers are ON/OFF and
optionally scales with PRB utilization (load-scaling factor).

Also manages the capacity-based decision parameters:
  capacity_ceiling (default 80%) - max load per active carrier
  target_band_low (default 70%)  - ideal low end of operating band
  target_band_high (default 80%) - ideal high end of operating band
"""

from __future__ import annotations

from sqlalchemy.orm import Session
from app import models


DEFAULTS = {
    "carrier_a_watts": 2400.0,
    "carrier_b_watts": 900.0,
    "carrier_c_watts": 900.0,
    "load_scaling_factor": 0.15,
    "capacity_ceiling": 80.0,
    "target_band_low": 70.0,
    "target_band_high": 80.0,
    "decision_logic": "capacity_based",
    "carrier_threshold": 70.0,
}


def get_power_config(db: Session) -> dict:
    """Load the power model configuration. Creates defaults if none exist."""
    cfg = db.query(models.PowerModelConfig).first()
    if not cfg:
        cfg = models.PowerModelConfig(**DEFAULTS)
        db.add(cfg)
        db.flush()
    return {
        "carrier_a_watts": cfg.carrier_a_watts,
        "carrier_b_watts": cfg.carrier_b_watts,
        "carrier_c_watts": cfg.carrier_c_watts,
        "load_scaling_factor": cfg.load_scaling_factor,
        "capacity_ceiling": cfg.capacity_ceiling,
        "target_band_low": cfg.target_band_low,
        "target_band_high": cfg.target_band_high,
        "decision_logic": cfg.decision_logic or "capacity_based",
        "carrier_threshold": cfg.carrier_threshold or 70.0,
    }


def set_power_config(db: Session, params: dict) -> dict:
    """Update the power model configuration."""
    cfg = db.query(models.PowerModelConfig).first()
    if not cfg:
        cfg = models.PowerModelConfig(**DEFAULTS)
        db.add(cfg)
        db.flush()
    for key in ("carrier_a_watts", "carrier_b_watts", "carrier_c_watts", "load_scaling_factor",
                "capacity_ceiling", "target_band_low", "target_band_high",
                "decision_logic", "carrier_threshold"):
        if key in params:
            setattr(cfg, key, params[key])
    db.flush()
    return get_power_config(db)


def compute_tower_power(
    carrier_a_on: bool,
    carrier_b_on: bool,
    carrier_c_on: bool,
    carrier_a_prb: float = 0.0,
    carrier_b_prb: float = 0.0,
    carrier_c_prb: float = 0.0,
    config: dict | None = None,
) -> float:
    """Compute total tower power in Watts.

    Each ON carrier draws its base watts, optionally scaled by its PRB utilization
    using the load_scaling_factor.
    """
    if config is None:
        config = DEFAULTS

    total = 0.0
    lsf = config["load_scaling_factor"]

    if carrier_a_on:
        total += config["carrier_a_watts"] * (1.0 + (carrier_a_prb / 100.0) * lsf)
    if carrier_b_on:
        total += config["carrier_b_watts"] * (1.0 + (carrier_b_prb / 100.0) * lsf)
    if carrier_c_on:
        total += config["carrier_c_watts"] * (1.0 + (carrier_c_prb / 100.0) * lsf)

    return round(total, 2)


def compute_max_tower_power(config: dict | None = None) -> float:
    """Compute the theoretical max power for a tower (all carriers ON at 100% PRB)."""
    return compute_tower_power(True, True, True, 100.0, 100.0, 100.0, config)


def compute_min_tower_power(config: dict | None = None) -> float:
    """Compute the theoretical min power for a tower (only Carrier A at 0% PRB)."""
    return compute_tower_power(True, False, False, 0.0, 0.0, 0.0, config)


def power_saved_watts(
    carrier_a_prb: float,
    carrier_b_prb: float,
    carrier_c_prb: float,
    carrier_b_on: bool,
    carrier_c_on: bool,
    config: dict | None = None,
) -> float:
    """Compute watts saved compared to all-carriers-ON baseline."""
    if config is None:
        config = DEFAULTS
    all_on = compute_tower_power(True, True, True, carrier_a_prb, carrier_b_prb, carrier_c_prb, config)
    actual = compute_tower_power(True, carrier_b_on, carrier_c_on, carrier_a_prb, carrier_b_prb, carrier_c_prb, config)
    return round(all_on - actual, 2)


def capacity_decide(
    carrier_loads: list[dict],
    ceiling: float,
) -> dict:
    """Capacity-based decision algorithm.

    Given a list of carrier dicts sorted by activation_order (0,1,2,...),
    each with a 'predicted_prb' and 'sector_label', determine how many
    carriers must be active so that total_demand / active_count <= ceiling.

    Returns dict with carrier states, total_demand, active_count, mode.
    """
    total_demand = sum(c.get("predicted_prb", 0) or 0 for c in carrier_loads)

    # Try increasing numbers of active carriers (min=1, always start with order 0)
    active_count = len(carrier_loads)  # fallback: all on
    for n in range(1, len(carrier_loads) + 1):
        if total_demand / n <= ceiling:
            active_count = n
            break

    # Assign ON/OFF based on activation_order
    result_carriers = []
    for c in carrier_loads:
        is_on = c["activation_order"] < active_count
        result_carriers.append({
            "sector_label": c["sector_label"],
            "activation_order": c["activation_order"],
            "predicted_prb": c.get("predicted_prb"),
            "is_on": is_on,
        })

    # Determine mode label
    if active_count >= len(carrier_loads):
        mode = "high"
    elif active_count == 1:
        mode = "power_saving"
    else:
        mode = "balanced"

    return {
        "total_demand": round(total_demand, 2),
        "capacity_ceiling": ceiling,
        "active_count": active_count,
        "max_carriers": len(carrier_loads),
        "per_carrier_load": round(total_demand / active_count, 2) if active_count > 0 else 0,
        "mode": mode,
        "carriers": result_carriers,
    }


def threshold_decide(
    carrier_loads: list[dict],
    threshold: float,
) -> dict:
    """Threshold-based decision algorithm.

    If ANY carrier's predicted_prb exceeds the threshold, ALL carriers are
    activated. Otherwise only the primary carrier (activation_order=0) stays on.

    Returns dict with carrier states, total_demand, active_count, mode.
    """
    total_demand = sum(c.get("predicted_prb", 0) or 0 for c in carrier_loads)

    any_above = any((c.get("predicted_prb", 0) or 0) > threshold for c in carrier_loads)
    active_count = len(carrier_loads) if any_above else 1

    result_carriers = []
    for c in carrier_loads:
        is_on = c["activation_order"] < active_count
        result_carriers.append({
            "sector_label": c["sector_label"],
            "activation_order": c["activation_order"],
            "predicted_prb": c.get("predicted_prb"),
            "is_on": is_on,
        })

    if active_count >= len(carrier_loads):
        mode = "high"
    elif active_count == 1:
        mode = "power_saving"
    else:
        mode = "balanced"

    return {
        "total_demand": round(total_demand, 2),
        "carrier_threshold": threshold,
        "active_count": active_count,
        "max_carriers": len(carrier_loads),
        "per_carrier_load": round(total_demand / active_count, 2) if active_count > 0 else 0,
        "mode": mode,
        "carriers": result_carriers,
    }
