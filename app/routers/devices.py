from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from ..database import get_db
from ..models import Device
from ..deps import get_api_key

router = APIRouter(tags=["devices"])

class DeviceIn(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    location: str | None = Field(default=None, max_length=255)

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
