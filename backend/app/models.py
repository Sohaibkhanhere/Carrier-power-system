from datetime import date, datetime
from sqlalchemy import (
    Column, Integer, Float, String, Date, DateTime, Boolean, ForeignKey, Text,
    UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from app.database import Base


class Site(Base):
    __tablename__ = "sites"
    id = Column(Integer, primary_key=True, autoincrement=True)
    enodeb_name = Column(String, nullable=False, unique=True)
    location = Column(String, default="")
    towers = relationship("Tower", back_populates="site", cascade="all, delete-orphan")


class Tower(Base):
    __tablename__ = "towers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("sites.id"), nullable=False)
    tower_label = Column(String, nullable=False)
    site = relationship("Site", back_populates="towers")
    carriers = relationship("Carrier", back_populates="tower", cascade="all, delete-orphan")


class Carrier(Base):
    __tablename__ = "carriers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tower_id = Column(Integer, ForeignKey("towers.id"), nullable=False)
    sector_label = Column(String, nullable=False)
    cell_name = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)
    activation_order = Column(Integer, default=0)
    tower = relationship("Tower", back_populates="carriers")
    kpi_records = relationship("KpiHourly", back_populates="carrier", cascade="all, delete-orphan")


class KpiHourly(Base):
    __tablename__ = "kpi_hourly"
    id = Column(Integer, primary_key=True, autoincrement=True)
    carrier_id = Column(Integer, ForeignKey("carriers.id"), nullable=False)
    date = Column(Date, nullable=False)
    hour = Column(Integer, nullable=False)
    traffic_users = Column(Float, default=0.0)
    prb_utilization = Column(Float, default=0.0)
    power_watts = Column(Float, default=0.0)
    source = Column(String, default="upload")
    carrier = relationship("Carrier", back_populates="kpi_records")
    __table_args__ = (
        UniqueConstraint("carrier_id", "date", "hour", name="uq_kpi_carrier_date_hour"),
        Index("ix_kpi_carrier_date", "carrier_id", "date"),
        Index("ix_kpi_date_hour", "date", "hour"),
    )


class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    carrier_id = Column(Integer, ForeignKey("carriers.id"), nullable=False)
    target_date = Column(Date, nullable=False)
    target_hour = Column(Integer, nullable=False)
    predicted_traffic = Column(Float)
    predicted_prb = Column(Float)
    model_version = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (
        Index("ix_pred_carrier_date", "carrier_id", "target_date"),
    )


class Decision(Base):
    __tablename__ = "decisions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    tower_id = Column(Integer, ForeignKey("towers.id"), nullable=False)
    date = Column(Date, nullable=False)
    hour = Column(Integer, nullable=False)
    mode = Column(String, nullable=False)
    carrier_b_state = Column(String, nullable=False)
    carrier_c_state = Column(String, nullable=False)
    predicted_prb_used = Column(Float)
    power_watts = Column(Float, default=0.0)
    total_demand = Column(Float, default=0.0)
    capacity_ceiling_used = Column(Float, default=80.0)
    active_count = Column(Integer, default=1)
    __table_args__ = (
        Index("ix_decisions_tower_date", "tower_id", "date"),
        Index("ix_decisions_date_hour", "date", "hour"),
    )


class ModelRun(Base):
    __tablename__ = "model_runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    trained_at = Column(DateTime, default=datetime.utcnow)
    model_type = Column(String, nullable=False)
    training_row_count = Column(Integer)
    mae = Column(Float)
    rmse = Column(Float)
    notes = Column(Text, default="")


class PowerModelConfig(Base):
    __tablename__ = "power_model_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    carrier_a_watts = Column(Float, default=2400.0)
    carrier_b_watts = Column(Float, default=900.0)
    carrier_c_watts = Column(Float, default=900.0)
    load_scaling_factor = Column(Float, default=0.15)
    capacity_ceiling = Column(Float, default=80.0)
    target_band_low = Column(Float, default=70.0)
    target_band_high = Column(Float, default=80.0)
    decision_logic = Column(String, default="threshold_based")
    carrier_threshold = Column(Float, default=70.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
