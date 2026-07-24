from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DATABASE_URL = f"sqlite:///{DB_DIR / 'carrier_power.db'}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _column_exists(table: str, column: str, conn) -> bool:
    result = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(row[1] == column for row in result)


def _index_exists(name: str, conn) -> bool:
    result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='index'")).fetchall()
    return any(row[0] == name for row in result)


def init_db():
    from app import models  # noqa: F401 – ensure models are registered
    Base.metadata.create_all(bind=engine)

    # Migration: add power_watts columns if missing
    with engine.connect() as conn:
        if not _column_exists("kpi_hourly", "power_watts", conn):
            conn.execute(text("ALTER TABLE kpi_hourly ADD COLUMN power_watts FLOAT DEFAULT 0.0"))
            conn.commit()

        if not _column_exists("decisions", "power_watts", conn):
            conn.execute(text("ALTER TABLE decisions ADD COLUMN power_watts FLOAT DEFAULT 0.0"))
            conn.commit()

        # v3 migration: activation_order on carriers
        if not _column_exists("carriers", "activation_order", conn):
            conn.execute(text("ALTER TABLE carriers ADD COLUMN activation_order INTEGER DEFAULT 0"))
            conn.commit()

        # v3 migration: capacity-based fields on decisions
        if not _column_exists("decisions", "total_demand", conn):
            conn.execute(text("ALTER TABLE decisions ADD COLUMN total_demand FLOAT DEFAULT 0.0"))
            conn.commit()
        if not _column_exists("decisions", "capacity_ceiling_used", conn):
            conn.execute(text("ALTER TABLE decisions ADD COLUMN capacity_ceiling_used FLOAT DEFAULT 80.0"))
            conn.commit()
        if not _column_exists("decisions", "active_count", conn):
            conn.execute(text("ALTER TABLE decisions ADD COLUMN active_count INTEGER DEFAULT 1"))
            conn.commit()

        # v3 migration: capacity config on power_model_config
        if not _column_exists("power_model_config", "capacity_ceiling", conn):
            conn.execute(text("ALTER TABLE power_model_config ADD COLUMN capacity_ceiling FLOAT DEFAULT 80.0"))
            conn.commit()
        if not _column_exists("power_model_config", "target_band_low", conn):
            conn.execute(text("ALTER TABLE power_model_config ADD COLUMN target_band_low FLOAT DEFAULT 70.0"))
            conn.commit()
        if not _column_exists("power_model_config", "target_band_high", conn):
            conn.execute(text("ALTER TABLE power_model_config ADD COLUMN target_band_high FLOAT DEFAULT 80.0"))
            conn.commit()

        # v4 migration: decision logic selector
        if not _column_exists("power_model_config", "decision_logic", conn):
            conn.execute(text("ALTER TABLE power_model_config ADD COLUMN decision_logic VARCHAR DEFAULT 'threshold_based'"))
            conn.commit()
        if not _column_exists("power_model_config", "carrier_threshold", conn):
            conn.execute(text("ALTER TABLE power_model_config ADD COLUMN carrier_threshold FLOAT DEFAULT 70.0"))
            conn.commit()

        # Add indexes for efficient date-range and weekday queries
        indexes = [
            ("ix_kpi_carrier_date", "CREATE INDEX IF NOT EXISTS ix_kpi_carrier_date ON kpi_hourly (carrier_id, date)"),
            ("ix_kpi_date_hour", "CREATE INDEX IF NOT EXISTS ix_kpi_date_hour ON kpi_hourly (date, hour)"),
            ("ix_pred_carrier_date", "CREATE INDEX IF NOT EXISTS ix_pred_carrier_date ON predictions (carrier_id, target_date)"),
            ("ix_decisions_tower_date", "CREATE INDEX IF NOT EXISTS ix_decisions_tower_date ON decisions (tower_id, date)"),
            ("ix_decisions_date_hour", "CREATE INDEX IF NOT EXISTS ix_decisions_date_hour ON decisions (date, hour)"),
        ]
        for name, sql in indexes:
            if not _index_exists(name, conn):
                conn.execute(text(sql))
        conn.commit()
