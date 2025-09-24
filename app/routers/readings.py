# app/routers/readings.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Reading, Device, PollutantThreshold, IdempotencyKey
from ..schemas import ReadingIn, ReadingOut
from ..deps import get_api_key, get_idempotency_key
from ..aqi import compute_aqi
from datetime import datetime

router = APIRouter(tags=["readings"])

@router.get("/devices/{device_id}/history")
def get_history(
    device_id: str,
    minutes: int = Query(120, ge=1, le=525600),
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    since = datetime.now(timezone.utc) - timedelta(minutes=minutes)

    rows = (
        db.query(Reading.sensor_type, Reading.measured_at, Reading.value)
        .filter(Reading.device_id == device_id, Reading.measured_at >= since)
        .order_by(Reading.measured_at.asc())
        .all()
    )

    # Return a frontend-friendly shape
    return {
        "rows": [
            {
                "sensor_type": st,
                "measured_at": ts.isoformat().replace("+00:00", "Z") if hasattr(ts, "isoformat") else str(ts),
                "value": float(val) if val is not None else None,
            }
            for (st, ts, val) in rows
        ]
    }

def compute_alert(db: Session, sensor_type: str, value: float):
    """
    Return (aqi:int|None, alert:bool, aqi_category:str|None)
    Alert rule: AQI >= 101 OR (fallback) value >= warn threshold if AQI not available.
    """
    aqi, cat = compute_aqi(sensor_type, value)
    if aqi is not None:
        return aqi, (aqi >= 101), cat

    th = db.query(PollutantThreshold).filter_by(sensor_type=sensor_type).first()
    if not th:
        return None, False, None
    return None, (value >= th.warn), None

@router.post("/readings", response_model=ReadingOut)
def create_reading(
    body: ReadingIn,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
    idem_key: str | None = Depends(get_idempotency_key),
):
    # Ensure device exists
    dev = db.query(Device).filter_by(device_id=body.device_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found. Insert into devices first.")

    # Idempotency handling
    if idem_key:
        existing = db.query(IdempotencyKey).filter_by(key=idem_key).first()
        from hashlib import sha256
        payload_hash = sha256(str(sorted(body.dict().items())).encode()).hexdigest()
        if existing:
            if existing.request_hash != payload_hash:
                raise HTTPException(status_code=409, detail="Idempotency key reuse with different payload")
            # if same, return existing reading if present
            r0 = db.query(Reading).filter_by(idempotency_key=idem_key).order_by(Reading.id.desc()).first()
            if r0:
                return ReadingOut(
                    id=r0.id, device_id=r0.device_id, sensor_type=r0.sensor_type,
                    measured_at=r0.measured_at, value=r0.value, aqi=r0.aqi,
                    alert_flag=r0.alert_flag, aqi_category=compute_aqi(r0.sensor_type, r0.value)[1] if r0.aqi is not None else None
                )
        else:
            db.add(IdempotencyKey(key=idem_key, request_hash=payload_hash, status="in_progress"))
            db.flush()

    # Compute AQI + alert
    aqi, alert, aqi_cat = compute_alert(db, body.sensor_type, body.value)

    # Insert
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
        # unique constraint fallback
        exist = db.query(Reading).filter_by(
            device_id=body.device_id, sensor_type=body.sensor_type, measured_at=body.measured_at
        ).first()
        if exist:
            return ReadingOut(
                id=exist.id, device_id=exist.device_id, sensor_type=exist.sensor_type,
                measured_at=exist.measured_at, value=exist.value, aqi=exist.aqi,
                alert_flag=exist.alert_flag, aqi_category=compute_aqi(exist.sensor_type, exist.value)[1] if exist.aqi is not None else None
            )
        raise

    if idem_key:
        db.query(IdempotencyKey).filter_by(key=idem_key).update({"status": "succeeded"})
        db.commit()

    return ReadingOut(
        id=r.id, device_id=r.device_id, sensor_type=r.sensor_type,
        measured_at=r.measured_at, value=r.value, aqi=r.aqi,
        alert_flag=r.alert_flag, aqi_category=aqi_cat
    )

@router.get("/devices/{device_id}/readings", response_model=list[ReadingOut])
def list_readings(
    device_id: str,
    frm: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    sensor_type: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
):
    q = db.query(Reading).filter(Reading.device_id == device_id)
    if sensor_type: q = q.filter(Reading.sensor_type == sensor_type)
    if frm:         q = q.filter(Reading.measured_at >= frm)
    if to:          q = q.filter(Reading.measured_at < to)
    rows = q.order_by(Reading.measured_at.desc()).limit(limit).all()
    return [
        ReadingOut(
            id=r.id, device_id=r.device_id, sensor_type=r.sensor_type,
            measured_at=r.measured_at, value=r.value, aqi=r.aqi,
            alert_flag=r.alert_flag,
            aqi_category=compute_aqi(r.sensor_type, r.value)[1] if r.aqi is not None else None,
        ) for r in rows
    ]
