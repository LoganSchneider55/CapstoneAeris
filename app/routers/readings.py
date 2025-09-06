from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.orm import Session
from datetime import datetime
import hashlib
from ..database import get_db
from ..schemas import ReadingIn, ReadingOut
from ..models import Reading, Device, PollutantThreshold, IdempotencyKey
from ..deps import get_api_key

router = APIRouter(tags=["readings"])

def compute_alert(db: Session, sensor_type: str, value: float):
    th = db.query(PollutantThreshold).filter_by(sensor_type=sensor_type).first()
    if not th:
        return None, False
    alert = value >= th.warn
    return None, alert

def hash_body(payload: dict) -> str:
    b = str(sorted(payload.items())).encode("utf-8")
    import hashlib as _h
    return _h.sha256(b).hexdigest()

@router.post("/readings", response_model=ReadingOut)
def create_reading(
    body: ReadingIn,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
    idem_key: str | None = Header(default=None, alias="X-Idempotency-Key")
):
    dev = db.query(Device).filter_by(device_id=body.device_id).first()
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found. Insert into devices first.")

    if idem_key:
        payload_hash = hash_body(body.dict())
        existing = db.query(IdempotencyKey).filter_by(key=idem_key).first()
        if existing:
            if existing.request_hash != payload_hash:
                raise HTTPException(status_code=409, detail="Idempotency key reuse with different payload")
            r = db.query(Reading).filter_by(idempotency_key=idem_key).order_by(Reading.id.desc()).first()
            if r:
                return ReadingOut(
                    id=r.id, device_id=r.device_id, sensor_type=r.sensor_type,
                    measured_at=r.measured_at, value=r.value, aqi=r.aqi, alert_flag=r.alert_flag
                )
        else:
            db.add(IdempotencyKey(key=idem_key, request_hash=payload_hash, status="in_progress"))
            db.flush()

    aqi, alert = compute_alert(db, body.sensor_type, body.value)

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
    except Exception as e:
        db.rollback()
        existing_r = db.query(Reading).filter_by(
            device_id=body.device_id, sensor_type=body.sensor_type, measured_at=body.measured_at
        ).first()
        if existing_r:
            return ReadingOut(
                id=existing_r.id, device_id=existing_r.device_id, sensor_type=existing_r.sensor_type,
                measured_at=existing_r.measured_at, value=existing_r.value,
                aqi=existing_r.aqi, alert_flag=existing_r.alert_flag
            )
        raise

    if idem_key:
        db.query(IdempotencyKey).filter_by(key=idem_key).update({"status": "succeeded"})
        db.commit()

    return ReadingOut(
        id=r.id, device_id=r.device_id, sensor_type=r.sensor_type,
        measured_at=r.measured_at, value=r.value, aqi=r.aqi, alert_flag=r.alert_flag
    )

@router.get("/devices/{device_id}/readings", response_model=list[ReadingOut])
def list_readings(
    device_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(get_api_key),
    sensor_type: str | None = Query(default=None),
    frm: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000)
):
    q = db.query(Reading).filter(Reading.device_id == device_id)
    if sensor_type:
        q = q.filter(Reading.sensor_type == sensor_type)
    if frm:
        q = q.filter(Reading.measured_at >= frm)
    if to:
        q = q.filter(Reading.measured_at < to)
    q = q.order_by(Reading.measured_at.desc()).limit(limit)

    rows = q.all()
    return [
        ReadingOut(
            id=r.id, device_id=r.device_id, sensor_type=r.sensor_type,
            measured_at=r.measured_at, value=r.value, aqi=r.aqi, alert_flag=r.alert_flag
        ) for r in rows
    ]
