"""Pluggable data connector interface for live data ingestion.

Defines an abstract DataConnector protocol and ships working implementations:
  - MockConnector: generates simulated live data (demo/testing)
  - FileWatchConnector: watches an incoming folder for new CSV/XLSX files
  - ManualUploadConnector: wraps the existing upload endpoint logic

Adding a real vendor connector (Huawei U2020, Nokia NetAct, etc.) only
requires implementing the DataConnector protocol — no other changes needed.
"""

from __future__ import annotations

import abc
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app import models


class DataConnector(abc.ABC):
    """Abstract interface for data sources.

    Every connector must implement `fetch_latest(since)` which returns a
    DataFrame matching the expected KPI schema:
      Date, Time, Tower_Sector, eNodeB Name, Cell Name,
      L.Traffic.User.Avg, DL_PRB_Utilization(%)
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...

    @abc.abstractmethod
    def fetch_latest(self, since: datetime | None = None) -> pd.DataFrame:
        ...

    @abc.abstractmethod
    def is_available(self) -> bool:
        ...


# ──────────────────────────────────────────────────────────────────
# Mock Connector — generates simulated live data for demos
# ──────────────────────────────────────────────────────────────────

class MockConnector(DataConnector):
    """Generates simulated hourly KPI data using the calibrated shapes
    from the synthetic service."""

    @property
    def name(self) -> str:
        return "mock"

    def is_available(self) -> bool:
        return True

    def fetch_latest(self, since: datetime | None = None) -> pd.DataFrame:
        from app.services.synthetic import generate_synthetic_row

        now = datetime.now()
        target = now.replace(minute=0, second=0, microsecond=0)

        # Generate one hour of data for all carriers
        carriers_config = [
            ("1_A", "Tower_A_SectorA", "SADDAR1_S_1_A"),
            ("1_B", "Tower_A_SectorB", "SADDAR1_S_1_B"),
            ("1_C", "Tower_A_SectorC", "SADDAR1_S_1_C"),
            ("2_A", "Tower_B_SectorA", "SADDAR1_S_2_A"),
            ("2_B", "Tower_B_SectorB", "SADDAR1_S_2_B"),
            ("2_C", "Tower_B_SectorC", "SADDAR1_S_2_C"),
        ]

        rows = []
        for sector, cell_name, _ in carriers_config:
            traffic, prb = generate_synthetic_row(sector, target.date(), target.hour)
            rows.append({
                "Date": target.strftime("%Y-%m-%d"),
                "Time": f"{target.hour:02d}:00",
                "Tower_Sector": sector,
                "eNodeB Name": "KHI0080H_SADDAR1_S",
                "Cell Name": cell_name,
                "L.Traffic.User.Avg": traffic,
                "DL_PRB_Utilization(%)": prb,
            })

        return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────
# File Watch Connector — watches an "incoming" folder
# ──────────────────────────────────────────────────────────────────

class FileWatchConnector(DataConnector):
    """Watches a designated folder for new CSV/XLSX files.

    Processed files are moved to a 'processed' subfolder.
    """

    def __init__(self, watch_dir: str = "incoming"):
        self.watch_dir = Path(watch_dir)
        self.processed_dir = self.watch_dir / "processed"
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    @property
    def name(self) -> str:
        return "file_watch"

    def is_available(self) -> bool:
        return self.watch_dir.exists()

    def fetch_latest(self, since: datetime | None = None) -> pd.DataFrame:
        frames = []
        for f in sorted(self.watch_dir.glob("*")):
            if f.suffix.lower() in (".csv", ".xlsx", ".xls"):
                try:
                    if f.suffix.lower() == ".csv":
                        df = pd.read_csv(f)
                    else:
                        df = pd.read_excel(f)
                    frames.append(df)
                    # Move to processed
                    dest = self.processed_dir / f.name
                    f.rename(dest)
                except Exception:
                    continue

        if frames:
            return pd.concat(frames, ignore_index=True)
        return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────
# Connector Registry & Auto-Ingestion
# ──────────────────────────────────────────────────────────────────

_CONNECTORS: dict[str, DataConnector] = {}


def register_connector(connector: DataConnector) -> None:
    _CONNECTORS[connector.name] = connector


def get_connector(name: str) -> DataConnector | None:
    return _CONNECTORS.get(name)


def list_connectors() -> list[dict]:
    return [
        {"name": c.name, "available": c.is_available()}
        for c in _CONNECTORS.values()
    ]


# Register default connectors
register_connector(MockConnector())
register_connector(FileWatchConnector())


def ingest_from_connector(name: str, db: Session) -> dict:
    """Pull data from a named connector and upsert into the DB.

    Returns ingestion summary.
    """
    from app.services.import_service import import_dataframe

    connector = get_connector(name)
    if not connector:
        return {"error": f"Unknown connector: {name}"}

    if not connector.is_available():
        return {"error": f"Connector '{name}' is not available"}

    df = connector.fetch_latest()
    if df.empty:
        return {"rows_accepted": 0, "rows_rejected": 0, "message": "No new data from connector"}

    accepted, errors = import_dataframe(df, db, source=f"live_{name}")
    db.flush()

    return {
        "connector": name,
        "rows_accepted": accepted,
        "rows_rejected": len(df) - accepted,
        "errors": errors,
    }


def should_retrain(db: Session, threshold_days: int = 7) -> bool:
    """Check if enough new live data has accumulated to trigger retraining.

    Compares count of 'live_*' source rows since last training run.
    """
    last_run = (
        db.query(models.ModelRun)
        .order_by(models.ModelRun.trained_at.desc())
        .first()
    )

    if not last_run:
        # No training has happened — check if we have enough seed data
        total = db.query(models.KpiHourly).count()
        return total >= 100

    # Count live rows since last training
    live_count = (
        db.query(models.KpiHourly)
        .filter(
            models.KpiHourly.source.like("live_%"),
            models.KpiHourly.date >= last_run.trained_at.date() if last_run.trained_at else True,
        )
        .count()
    )

    return live_count >= threshold_days * 24 * 6  # threshold_days * hours * carriers
