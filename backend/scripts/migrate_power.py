"""Recompute power_watts for all existing KPI rows and decision rows."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date
from sqlalchemy import func
from app.database import SessionLocal, init_db
from app.models import KpiHourly, Decision, Carrier, Tower
from app.services.power import get_power_config, compute_tower_power


def main():
    init_db()
    db = SessionLocal()

    try:
        pconfig = get_power_config(db)
        print(f"Power config: A={pconfig['carrier_a_watts']}W, B={pconfig['carrier_b_watts']}W, C={pconfig['carrier_c_watts']}W, LSF={pconfig['load_scaling_factor']}")

        # Update all KPI rows with power_watts = 0 to get a baseline
        # For KPI rows, power_watts represents the carrier's individual draw
        # We'll compute tower-level power in the decisions table instead
        print("\nUpdating KPI rows with carrier-level power estimates...")

        carriers = db.query(Carrier).all()
        carrier_map = {c.id: c for c in carriers}
        carrier_configs = {
            "A": pconfig["carrier_a_watts"],
            "B": pconfig["carrier_b_watts"],
            "C": pconfig["carrier_c_watts"],
        }
        lsf = pconfig["load_scaling_factor"]

        batch_size = 5000
        total = db.query(func.count(KpiHourly.id)).scalar()
        print(f"Total KPI rows: {total}")

        updated = 0
        for kpi in db.query(KpiHourly).yield_per(batch_size):
            carrier = carrier_map.get(kpi.carrier_id)
            if carrier:
                sector = carrier.sector_label.split("_")[1]
                base_watts = carrier_configs.get(sector, 0)
                # Scale with PRB if not primary (optional load-scaling)
                if sector != "A":
                    kpi.power_watts = round(base_watts * (1.0 + (kpi.prb_utilization / 100.0) * lsf), 2)
                else:
                    kpi.power_watts = round(base_watts * (1.0 + (kpi.prb_utilization / 100.0) * lsf), 2)
                updated += 1

        db.flush()
        print(f"Updated {updated} KPI rows with power_watts.")

        # Update decisions with tower-level power
        print("\nUpdating decision rows with tower power...")
        towers = db.query(Tower).all()
        tower_carriers = {}
        for t in towers:
            tower_carriers[t.id] = sorted(t.carriers, key=lambda c: c.sector_label)

        dec_total = db.query(func.count(Decision.id)).scalar()
        print(f"Total decision rows: {dec_total}")

        dec_updated = 0
        for dec in db.query(Decision).yield_per(batch_size):
            t_carriers = tower_carriers.get(dec.tower_id, [])
            ca_on = cb_on = cc_on = True
            ca_prb = cb_prb = cc_prb = 50.0

            for c in t_carriers:
                sector = c.sector_label.split("_")[1]
                if sector == "A":
                    ca_on = True
                elif sector == "B":
                    cb_on = dec.carrier_b_state == "ON"
                    cb_prb = dec.predicted_prb_used or 50
                elif sector == "C":
                    cc_on = dec.carrier_c_state == "ON"
                    cc_prb = dec.predicted_prb_used or 50

            dec.power_watts = compute_tower_power(ca_on, cb_on, cc_on, ca_prb, cb_prb, cc_prb, pconfig)
            dec_updated += 1

        db.commit()
        print(f"Updated {dec_updated} decision rows with tower power_watts.")
        print("\nMigration complete!")

    finally:
        db.close()


if __name__ == "__main__":
    main()
