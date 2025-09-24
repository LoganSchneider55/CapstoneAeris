# app/routers/devices.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from ..database import get_db
from ..models import Device, Reading          # <-- add Reading import
from ..deps import get_api_key

router = APIRouter(tags=["devices"])

# ---------- models for input ----------
from pydantic import BaseModel, Field

class DeviceIn(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    location: str | None = Field(default=None, max_length=255)

# ---------- existing endpoint ----------
@router.post("/devices")
def register_device(
    body: DeviceIn,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    # Upsert behaviour: update if exists, otherwise create
    existing = db.query(Device).filter_by(device_id=body.device_id).first()
    if existing:
        existing.name = body.name
        existing.location = body.location
        db.commit()
        return {"ok": True, "updated": True, "device_id": existing.device_id}

    db.add(Device(device_id=body.device_id, name=body.name, location=body.location))
    db.commit()
    return {"ok": True, "created": True, "device_id": body.device_id}

# ---------- NEW: latest per sensor ----------
@router.get("/devices/{device_id}/latest")
def get_latest_per_sensor(
    device_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    """
    Returns the most recent reading for each sensor_type for this device.
    Shape: { temperature, humidity, pressure, pm25, voc, co, measured_at }
    """

    # subquery: max(measured_at) per sensor_type for this device
    subq = (
        db.query(
            Reading.sensor_type.label("sensor_type"),
            func.max(Reading.measured_at).label("max_t"),
        )
        .filter(Reading.device_id == device_id)
        .group_by(Reading.sensor_type)
        .subquery()
    )

    # join back to get the rows at those max timestamps
    rows = (
        db.query(Reading.sensor_type, Reading.measured_at, Reading.value)
        .join(
            subq,
            and_(
                Reading.sensor_type == subq.c.sensor_type,
                Reading.measured_at == subq.c.max_t,
            ),
        )
        .filter(Reading.device_id == device_id)
        .all()
    )

    if not rows:
        # 404 is fine; your React handles empty/404 gracefully
        raise HTTPException(status_code=404, detail="No readings found for this device")

    # map DB sensor_type -> frontend keys
    alias = {
        "pm25": "pm25",
        "voc": "voc",
        "co": "co",
        "temperature_c": "temperature",
        "humidity": "humidity",
        "pressure_hpa": "pressure",
    }

    out = {}
    latest_ts = None
    for sensor_type, measured_at, value in rows:
        key = alias.get(sensor_type)
        if not key:
            continue
        out[key] = float(value)
        # track the newest timestamp among sensors
        if latest_ts is None or str(measured_at) > str(latest_ts):
            latest_ts = measured_at

    if latest_ts is not None:
        out["measured_at"] = str(latest_ts)

    # if you store fan status somewhere, set it here; else default False
    out.setdefault("fanStatus", False)

    return out
