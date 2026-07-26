from app.database import SessionLocal, init_db
from app.services import ml_model, decision
from app import models
from sqlalchemy import func
from datetime import timedelta

init_db()
db = SessionLocal()
try:
    print("Training ML models...")
    results = ml_model.train_all_carriers(db)
    db.commit()
    for r in results:
        print(f"  Carrier {r['carrier_id']}: MAE={r['mae']:.2f}%, RMSE={r['rmse']:.2f}%")
    print(f"Total: {len(results)} models trained\n")

    print("Regenerating decisions with threshold logic...")
    max_date = db.query(func.max(models.KpiHourly.date)).scalar()
    min_date = db.query(func.min(models.KpiHourly.date)).scalar()
    if min_date and max_date:
        count = decision.make_decisions_for_range(min_date, max_date, db)
        db.commit()
        print(f"Generated {count} decisions ({min_date} to {max_date})")
    else:
        print("No data dates found")

    print("\nRetraining ML models again (with fresh predictions)...")
    results2 = ml_model.train_all_carriers(db)
    db.commit()
    for r in results2:
        print(f"  Carrier {r['carrier_id']}: MAE={r['mae']:.2f}%, RMSE={r['rmse']:.2f}%")
    print(f"Total: {len(results2)} models retrained")
except Exception as e:
    print("ERROR:", e)
    import traceback
    traceback.print_exc()
    db.rollback()
finally:
    db.close()
