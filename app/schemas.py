# app/schemas.py
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# ---------- Input schema ----------
class ReadingIn(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    sensor_type: str = Field(min_length=1, max_length=32)
    measured_at: datetime
    value: float


# ---------- Output schema ----------
class ReadingOut(BaseModel):
    # Pydantic v2: enable from_orm() / from_attributes()
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    device_id: str
    sensor_type: str
    measured_at: datetime
    value: float
    aqi: Optional[int] = None
    alert_flag: int
    # Filled in by the route after computing AQI
    aqi_category: Optional[str] = None
