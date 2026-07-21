"""Live ingestion API — connector management, manual triggers, auto-retrain."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import connector

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


@router.get("/connectors")
def list_connectors():
    """List all registered data connectors and their availability."""
    return connector.list_connectors()


@router.post("/pull/{name}")
def pull_from_connector(name: str, db: Session = Depends(get_db)):
    """Pull latest data from a named connector and ingest into DB."""
    result = connector.ingest_from_connector(name, db)
    if "error" in result:
        db.rollback()
    else:
        db.commit()
    return result


@router.get("/retrain-check")
def retrain_check(db: Session = Depends(get_db)):
    """Check if enough new data has accumulated to trigger retraining."""
    should = connector.should_retrain(db)
    return {"should_retrain": should}


@router.post("/auto-pull-and-retrain")
def auto_pull_and_retrain(db: Session = Depends(get_db)):
    """Pull from all available connectors, then retrain if needed.

    This is the main loop endpoint — call it periodically or from a scheduler.
    """
    results = {"pull_results": [], "retrained": False}

    # Pull from all available connectors
    for c in connector.list_connectors():
        if c["available"]:
            pull_result = connector.ingest_from_connector(c["name"], db)
            results["pull_results"].append(pull_result)

    db.commit()

    # Check if retraining is needed
    if connector.should_retrain(db):
        from app.services.ml_model import train_all_carriers
        train_results = train_all_carriers(db)
        results["retrained"] = True
        results["training_results"] = train_results

    return results
