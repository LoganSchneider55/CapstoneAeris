from pydantic import BaseModel, Field
from datetime import datetime

class ReadingIn(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    sensor_type: str = Field(min_length=1, max_length=32)
    measured_at: datetime
    value: float

class ReadingOut(BaseModel):
    id: int
    device_id: str
    sensor_type: str
    measured_at: datetime
    value: float
    aqi: int | None
    alert_flag: bool
    aqi_category: str | None = None
