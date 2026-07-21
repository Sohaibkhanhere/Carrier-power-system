from datetime import date
from pydantic import BaseModel


class KpiRowOut(BaseModel):
    id: int
    carrier_sector: str
    cell_name: str
    tower_label: str
    date: date
    hour: int
    traffic_users: float
    prb_utilization: float
    source: str

    class Config:
        from_attributes = True


class UploadResult(BaseModel):
    rows_accepted: int
    rows_rejected: int
    errors: list[str]


class SiteOut(BaseModel):
    id: int
    enodeb_name: str
    location: str | None

    class Config:
        from_attributes = True


class TowerOut(BaseModel):
    id: int
    tower_label: str
    site_id: int

    class Config:
        from_attributes = True


class CarrierOut(BaseModel):
    id: int
    sector_label: str
    cell_name: str
    is_primary: bool
    tower_id: int

    class Config:
        from_attributes = True


class PredictionOut(BaseModel):
    carrier_id: int
    sector_label: str
    target_date: str
    target_hour: int
    predicted_prb: float | None
    predicted_traffic: float | None
    prb_min: float | None
    prb_max: float | None
    prb_std: float | None
    sample_count: int


class DecisionOut(BaseModel):
    id: int
    tower_label: str
    date: str
    hour: int
    mode: str
    carrier_b_state: str
    carrier_c_state: str
    predicted_prb_used: float | None


class ThresholdUpdate(BaseModel):
    threshold: float


class LiveStatus(BaseModel):
    date: str
    hour: int
    towers: dict
