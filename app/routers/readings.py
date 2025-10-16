# app/routers/readings.py
# Minimal, safe router for reading ingestion.
# - Stores RAW sensor_type as sent by device (e.g., "pm25_ugm3", "voc_index")
# - Uses canonical key only for AQI/threshold lookup (pm25, pm10, co, o3)
# - No schema changes required

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from .. import models, schemas, deps
from ..aqi import compute_aqi, canonical_pollutant
from ..database import get_db

router = APIRouter(prefix="/v1", tags=["readings"])


@router.post(
    "/readings",
    response_model=schemas.ReadingOut,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a single sensor reading"
)
def create_reading(
    reading: schemas.ReadingIn,
    db: Session = Depends(get_db),
    api_key: models.APIKey = Depends(deps.get_api_key),                  # Authorization: Bearer <key>
    idempo_key: Optional[str] = Depends(deps.get_idempotency_key),       # X-Idempotency-Key (optional)
):
    """
    Ingest one reading. Keeps the RAW sensor_type exactly as sent.
    AQI/thresholds are computed via canonical mapping (pm25_ugm3 -> pm25, pm10_ugm3 -> pm10, co_ppm -> co).
    """

    # --- Compute AQI/category using alias-aware lookup (no change to stored sensor_type)
    raw_type = reading.sensor_type  # keep exactly what the device sent
    aqi_val, aqi_category = compute_aqi(raw_type, reading.value)

    # --- Threshold lookup uses canonical pollutant key if available (falls back to raw)
    threshold_key = canonical_pollutant(raw_type) or raw_type
    threshold = (
        db.query(models.PollutantThreshold)
          .filter(models.PollutantThreshold.sensor_type == threshold_key)
          .one_or_none()
    )
    
    alert_flag = 0
    if threshold:
        # ✅ Use your actual column names: warn, danger
        warn = getattr(threshold, "warn", None)
        danger = getattr(threshold, "danger", None)
        if danger is not None and reading.value >= danger:
            alert_flag = 2
        elif warn is not None and reading.value >= warn:
            alert_flag = 1


    # --- Optionally touch device's last_seen_at if the device exists
    device = db.query(models.Device).filter(models.Device.device_id == reading.device_id).one_or_none()
    if device:
        try:
            # use the reading's timestamp; assume it's UTC ISO-8601 in schemas.ReadingIn
            device.last_seen_at = reading.measured_at
        except Exception:
            # be graceful if anything odd about the timestamp object
            device.last_seen_at = datetime.utcnow()

    # --- Build the row (store RAW sensor_type)
    row = models.Reading(
        device_id=reading.device_id,
        sensor_type=raw_type,             # store exactly what was sent (e.g., "pm25_ugm3", "voc_index")
        measured_at=reading.measured_at,
        value=reading.value,
        aqi=aqi_val,                      # may be None for unsupported sensors (pm1_ugm3, voc_index, etc.)
        alert_flag=alert_flag,
        api_key=api_key.key,              # record which key wrote it (matches your schema)
        idempotency_key=idempo_key,       # optional; unique if you enforce it
    )

    # --- Insert safely: rely on unique (device_id, sensor_type, measured_at) to dedupe
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
    except IntegrityError:
        # Duplicate insert (same device_id/sensor_type/measured_at) → return the existing row
        db.rollback()
        existing = (
            db.query(models.Reading)
            .filter(models.Reading.device_id == reading.device_id)
            .filter(models.Reading.sensor_type == raw_type)
            .filter(models.Reading.measured_at == reading.measured_at)
            .one_or_none()
        )
        if not existing:
            # If somehow we failed to find it, raise a 409 to be explicit
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Duplicate reading and existing row could not be retrieved."
            )
        row = existing

    # --- Shape the response
    out = schemas.ReadingOut.from_orm(row)
    out.aqi_category = aqi_category if aqi_val is not None else "Unknown"
    return out


# (Optional) Keep a simple history endpoint here if your original file had it.
# If your original project already defines history elsewhere, you can delete this.

@router.get(
    "/devices/{device_id}/history",
    response_model=List[schemas.ReadingOut],
    summary="Fetch recent readings for a device",
)
def get_history(
    device_id: str,
    minutes: Optional[int] = None,
    sensor_type: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = 500,
    db: Session = Depends(get_db),
    _api_key: models.APIKey = Depends(deps.get_api_key),  # keep same auth behavior as the rest of your API
):
    """
    Basic history: filter by device, optional sensor_type and time window.
    This is a minimal version; keep your original if it has richer behavior.
    """
    q = db.query(models.Reading).filter(models.Reading.device_id == device_id)

    if sensor_type:
        q = q.filter(models.Reading.sensor_type == sensor_type)

    # Time window: prefer explicit since/until; otherwise support 'minutes'
    if since:
        q = q.filter(models.Reading.measured_at >= since)
    if until:
        q = q.filter(models.Reading.measured_at <= until)
    if minutes and not since and not until:
        # recent N minutes from "now" (DB time context)
        # If your original used UTC_TIMESTAMP(6) semantics, keep it as-is there.
        cutoff = datetime.utcnow()
        q = q.filter(models.Reading.measured_at >= cutoff.replace(microsecond=0))

    q = q.order_by(models.Reading.measured_at.desc()).limit(max(1, min(limit, 5000)))
    rows = q.all()

    # Attach AQI category dynamically for convenience
    out: List[schemas.ReadingOut] = []
    for r in rows:
        item = schemas.ReadingOut.from_orm(r)
        aqi_val, aqi_cat = compute_aqi(r.sensor_type, r.value)
        item.aqi_category = aqi_cat if aqi_val is not None else "Unknown"
        out.append(item)
    return out
