# app/routers/readings.py (only the changed parts)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session   # ✅ needed for type hints and DB session
from ..database import get_db
from ..models import Reading, PollutantThreshold
from ..schemas import ReadingIn, ReadingOut
from ..deps import get_api_key, get_idempotency_key
from ..aqi import compute_aqi

def compute_alert(db: Session, sensor_type: str, value: float):
    """
    Return (aqi:int|None, alert:bool, aqi_category:str|None)
    Alert rule: AQI >= 101 OR (fallback) value >= warn threshold if AQI not available.
    """
    aqi, cat = compute_aqi(sensor_type, value)
    if aqi is not None:
        return aqi, (aqi >= 101), cat

    # Fallback to your thresholds table if AQI not defined for this sensor
    th = db.query(PollutantThreshold).filter_by(sensor_type=sensor_type).first()
    if not th:
        return None, False, None
    return None, (value >= th.warn), None

@router.post("/readings", response_model=ReadingOut)
def create_reading(
    body: ReadingIn,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
    idem_key: str = Depends(get_idempotency_key),
):
    # Compute AQI + alert
    aqi, alert, aqi_cat = compute_alert(db, body.sensor_type, body.value)

    try:
        r = Reading(
            device_id=body.device_id,
            sensor_type=body.sensor_type,
            measured_at=body.measured_at,
            value=body.value,
            aqi=aqi,
            alert_flag=alert,
            api_key=api_key,
            idempotency_key=idem_key
        )
        db.add(r)
        db.commit()
        db.refresh(r)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflict: duplicate or invalid insert")

    return ReadingOut(
        id=r.id,
        device_id=r.device_id,
        sensor_type=r.sensor_type,
        measured_at=r.measured_at,
        value=r.value,
        aqi=r.aqi,
        alert_flag=r.alert_flag,
        aqi_category=aqi_cat,
    )

@router.get("/devices/{device_id}/readings", response_model=list[ReadingOut])
def list_readings(
    device_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    # Query the DB for recent readings for this device
    rows = (
        db.query(Reading)
        .filter(Reading.device_id == device_id)
        .order_by(Reading.measured_at.desc())
        .limit(limit)
        .all()
    )

    # Return API model with AQI category string attached
    return [
        ReadingOut(
            id=r.id,
            device_id=r.device_id,
            sensor_type=r.sensor_type,
            measured_at=r.measured_at,
            value=r.value,
            aqi=r.aqi,
            alert_flag=r.alert_flag,
            aqi_category=compute_aqi(r.sensor_type, r.value)[1]
            if r.aqi is not None
            else None,
        )
        for r in rows
    ]
