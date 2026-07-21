"""Admin panel API — password-protected settings, connector config, retrain."""

import json
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

router = APIRouter(prefix="/api/admin", tags=["admin"])

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CONNECTOR_CONFIG_PATH = CONFIG_DIR / "connector_config.json"


def _get_admin_password():
    return os.environ.get("ADMIN_PASSWORD", "admin123")


def _verify_password(x_admin_password: str = Header(None)):
    if x_admin_password != _get_admin_password():
        raise HTTPException(status_code=401, detail="Invalid admin password")


def _load_connector_config() -> dict:
    if CONNECTOR_CONFIG_PATH.exists():
        return json.loads(CONNECTOR_CONFIG_PATH.read_text())
    return {
        "enabled": False,
        "connector_type": "generic_rest",
        "base_url": "",
        "api_key": "",
        "username": "",
        "password": "",
        "poll_interval_seconds": 300,
    }


def _save_connector_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONNECTOR_CONFIG_PATH.write_text(json.dumps(config, indent=2))


@router.post("/login")
def admin_login(body: dict):
    """Verify admin password. Returns success/failure."""
    pw = body.get("password", "")
    if pw == _get_admin_password():
        return {"ok": True}
    raise HTTPException(status_code=401, detail="Invalid password")


@router.get("/connector-config")
def get_connector_config(_=Depends(_verify_password)):
    return _load_connector_config()


@router.post("/connector-config")
def set_connector_config(body: dict, _=Depends(_verify_password)):
    _save_connector_config(body)
    return {"ok": True}


@router.get("/power-config")
def get_power_config(_=Depends(_verify_password), db: Session = Depends(get_db)):
    from app.services.power import get_power_config as _get
    return _get(db)


@router.post("/power-config")
def set_power_config(body: dict, _=Depends(_verify_password), db: Session = Depends(get_db)):
    from app.services.power import set_power_config as _set
    result = _set(db, body)
    db.commit()
    return result


@router.post("/retrain")
def retrain_all(_=Depends(_verify_password), db: Session = Depends(get_db)):
    from app.services.ml_model import train_all_carriers
    results = train_all_carriers(db)
    return {"trained": len(results), "results": results}


@router.get("/model-runs")
def model_runs(limit: int = 20, _=Depends(_verify_password), db: Session = Depends(get_db)):
    from app.services.ml_model import get_model_runs
    return get_model_runs(db, limit)


@router.get("/db-audit")
def db_audit(_=Depends(_verify_password), db: Session = Depends(get_db)):
    return {
        "kpi_rows": db.query(models.KpiHourly).count(),
        "predictions": db.query(models.Prediction).count(),
        "decisions": db.query(models.Decision).count(),
        "model_runs": db.query(models.ModelRun).count(),
        "carriers": db.query(models.Carrier).count(),
        "towers": db.query(models.Tower).count(),
    }
