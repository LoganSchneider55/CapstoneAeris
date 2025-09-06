from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from .database import get_db
from .models import APIKey

def get_api_key(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    key = authorization.split(" ", 1)[1]
    api_key = db.query(APIKey).filter_by(key=key).first()
    if not api_key or api_key.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return key
