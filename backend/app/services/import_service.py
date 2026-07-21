"""Import Excel/CSV data and upsert into the database."""

from __future__ import annotations

import io
from datetime import datetime, time as dt_time
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app import models

REQUIRED_COLUMNS = [
    "Date",
    "Time",
    "Tower_Sector",
    "eNodeB Name",
    "Cell Name",
    "L.Traffic.User.Avg",
    "DL_PRB_Utilization(%)",
]


def _ensure_site(db: Session, enodeb_name: str) -> models.Site:
    site = db.query(models.Site).filter_by(enodeb_name=enodeb_name).first()
    if not site:
        site = models.Site(enodeb_name=enodeb_name, location="")
        db.add(site)
        db.flush()
    return site


def _ensure_tower(db: Session, site_id: int, sector_prefix: str) -> models.Tower:
    """Tower label derived from sector prefix: '1' -> 'Tower A', '2' -> 'Tower B'."""
    tower_label = f"Tower {chr(64 + int(sector_prefix))}"  # 1->A, 2->B
    tower = (
        db.query(models.Tower)
        .filter_by(site_id=site_id, tower_label=tower_label)
        .first()
    )
    if not tower:
        tower = models.Tower(site_id=site_id, tower_label=tower_label)
        db.add(tower)
        db.flush()
    return tower


def _ensure_carrier(
    db: Session, tower_id: int, sector_label: str, cell_name: str
) -> models.Carrier:
    carrier = (
        db.query(models.Carrier)
        .filter_by(tower_id=tower_id, sector_label=sector_label)
        .first()
    )
    if carrier:
        carrier.cell_name = cell_name  # update cell_name if changed
    else:
        is_primary = sector_label.endswith("_A")
        # Derive activation_order from sector suffix: _A=0, _B=1, _C=2, etc.
        suffix = sector_label.split("_")[-1].upper()
        activation_order = ord(suffix) - ord("A") if len(suffix) == 1 and suffix.isalpha() else 0
        carrier = models.Carrier(
            tower_id=tower_id,
            sector_label=sector_label,
            cell_name=cell_name,
            is_primary=is_primary,
            activation_order=activation_order,
        )
        db.add(carrier)
        db.flush()
    return carrier


def _parse_date(raw) -> datetime:
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, pd.Timestamp):
        return raw.to_pydatetime()
    s = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(s)


def _parse_time(raw) -> dt_time:
    if isinstance(raw, dt_time):
        return raw
    if isinstance(raw, datetime):
        return raw.time()
    s = str(raw).strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    parts = s.split(":")
    return dt_time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)


def import_dataframe(
    df: pd.DataFrame, db: Session, source: str = "upload"
) -> tuple[int, list[str]]:
    """Upsert rows from a DataFrame. Returns (accepted_count, error_messages)."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return 0, [f"Missing required columns: {', '.join(missing)}"]

    accepted = 0
    errors: list[str] = []

    for idx, row in df.iterrows():
        try:
            dt = _parse_date(row["Date"])
            tm = _parse_time(row["Time"])
            sector = str(row["Tower_Sector"]).strip()
            enodeb = str(row["eNodeB Name"]).strip()
            cell = str(row["Cell Name"]).strip()
            traffic = float(row["L.Traffic.User.Avg"])
            prb = float(row["DL_PRB_Utilization(%)"])

            tower_prefix = sector.split("_")[0]
            site = _ensure_site(db, enodeb)
            tower = _ensure_tower(db, site.id, tower_prefix)
            carrier = _ensure_carrier(db, tower.id, sector, cell)

            existing = (
                db.query(models.KpiHourly)
                .filter_by(carrier_id=carrier.id, date=dt.date(), hour=tm.hour)
                .first()
            )
            if existing:
                existing.traffic_users = traffic
                existing.prb_utilization = prb
                existing.source = source
            else:
                db.add(
                    models.KpiHourly(
                        carrier_id=carrier.id,
                        date=dt.date(),
                        hour=tm.hour,
                        traffic_users=traffic,
                        prb_utilization=prb,
                        source=source,
                    )
                )
            accepted += 1
        except Exception as exc:
            errors.append(f"Row {idx + 2}: {exc}")

    db.flush()
    return accepted, errors


def import_file_bytes(
    file_bytes: bytes, filename: str, db: Session, source: str = "upload"
) -> tuple[int, int, list[str]]:
    """Read a CSV or XLSX from raw bytes. Returns (accepted, rejected, errors)."""
    lower = filename.lower()
    if lower.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(file_bytes))
    elif lower.endswith((".xlsx", ".xls")):
        df = pd.read_excel(io.BytesIO(file_bytes))
    else:
        return 0, 0, [f"Unsupported file type: {filename}"]

    accepted, errors = import_dataframe(df, db, source=source)
    rejected = len(df) - accepted + len(errors)
    return accepted, max(rejected, 0), errors


def seed_file(path: str | Path, db: Session) -> tuple[int, list[str]]:
    """Import a seed Excel file with per-sheet processing."""
    path = Path(path)
    xl = pd.ExcelFile(path)
    total_accepted = 0
    all_errors: list[str] = []

    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        n, errs = import_dataframe(df, db, source="seed")
        total_accepted += n
        all_errors.extend(f"[{sheet}] {e}" for e in errs)

    return total_accepted, all_errors
