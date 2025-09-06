from fastapi import FastAPI
from .routers import readings
from .database import check_db

app = FastAPI(title="Aeris API", version="0.1.0")

@app.get("/healthz")
def healthz():
    ok, msg = check_db()
    return {"status": "ok" if ok else "error", "db": msg}

app.include_router(readings.router, prefix="/v1")
