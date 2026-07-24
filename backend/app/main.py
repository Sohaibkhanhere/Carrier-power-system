from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
import logging

from app.database import init_db
from app.routers import upload, data, predictions, export, ml, ingest, admin

logger = logging.getLogger("startup")

app = FastAPI(title="Carrier Power System", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://carrier-power-system.netlify.app",
        "https://mellifluous-sorbet-ef7b97.netlify.app",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(data.router)
app.include_router(predictions.router)
app.include_router(export.router)
app.include_router(ml.router)
app.include_router(ingest.router)
app.include_router(admin.router)


@app.on_event("startup")
def on_startup():
    init_db()

    from app.database import SessionLocal
    db = SessionLocal()
    try:
        from app.services import synthetic, ml_model
        from app import models

        carrier_count = db.query(models.Carrier).count()
        if carrier_count == 0:
            logger.info("No carriers found — skipping auto-fill and training.")
            return

        logger.info("Auto-filling synthetic data to current time...")
        inserted = synthetic.generate_synthetic_gap(db)
        db.commit()
        logger.info(f"Synthetic fill: {inserted} rows inserted.")

        max_date = db.query(func.max(models.KpiHourly.date)).scalar()
        min_date = db.query(func.min(models.KpiHourly.date)).scalar()
        existing_decisions = db.query(models.Decision).count()
        if existing_decisions == 0 and max_date:
            from datetime import timedelta
            from app.services import decision
            dec_start = max_date - timedelta(days=6)
            logger.info(f"Generating decisions for {dec_start} to {max_date}...")
            dc = decision.make_decisions_for_range(dec_start, max_date, db)
            db.commit()
            logger.info(f"Generated {dc} decision records.")
        else:
            logger.info(f"Decision records already exist ({existing_decisions}). Skipping.")

        existing_runs = db.query(models.ModelRun).count()
        if existing_runs == 0:
            logger.info("No ML model runs found — training all carriers...")
            results = ml_model.train_all_carriers(db)
            db.commit()
            logger.info(f"Auto-trained {len(results)} ML models.")
        else:
            logger.info(f"ML models already trained ({existing_runs} runs). Skipping.")
    except Exception as e:
        logger.error(f"Startup auto-fill/train failed: {e}")
        db.rollback()
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok"}
