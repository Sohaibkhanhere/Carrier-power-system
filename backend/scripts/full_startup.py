"""Full startup: seed + generate synthetic data + decisions + start server."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import date, timedelta
from sqlalchemy import func
from app.database import SessionLocal, init_db
from app.models import KpiHourly
from app.services.import_service import seed_file
from app.services import synthetic, decision

EXCEL_PATH = Path(__file__).resolve().parent.parent.parent / "One Month data.xlsx"


def main():
    print("=== Carrier Power System ===\n")

    print("1. Initialising database …")
    init_db()

    db = SessionLocal()
    try:
        print(f"2. Seeding from {EXCEL_PATH.name} …")
        count, errors = seed_file(EXCEL_PATH, db)
        db.commit()
        print(f"   Seeded {count} rows.")

        print("2b. Backfilling activation_order on carriers …")
        act_count = synthetic.ensure_carrier_activation_orders(db)
        db.commit()
        print(f"   Updated {act_count} carriers.")

        print("3. Generating synthetic data (bridge to today) …")
        synth_count = synthetic.generate_synthetic_gap(db)
        db.commit()
        print(f"   Generated {synth_count} synthetic rows.")

        print("4. Generating decisions for all data …")
        min_d = db.query(func.min(KpiHourly.date)).scalar()
        max_d = db.query(func.max(KpiHourly.date)).scalar()
        if min_d and max_d:
            dec_count = decision.make_decisions_for_range(min_d, max_d, db)
            db.commit()
            print(f"   Generated {dec_count} decision records.")
        else:
            print("   No data to generate decisions for.")
    finally:
        db.close()

    print("\n5. Starting server on http://localhost:8000 …\n")
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
