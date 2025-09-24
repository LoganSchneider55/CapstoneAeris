from fastapi import FastAPI
from .routers import readings, devices
from .database import check_db
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Aeris API", version="0.2.0")
# Cors
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        # add your deployed dashboard origin here later if needed
    ],
    allow_credentials=True,
    allow_methods=["*"],   # allows GET, POST, PATCH, OPTIONS, etc.
    allow_headers=["*"],   # allows Authorization, Content-Type, etc.
)

@app.get("/healthz")
def healthz():
    ok, msg = check_db()
    return {"status": "ok" if ok else "error", "db": msg}

app.include_router(readings.router, prefix="/v1")
app.include_router(devices.router,  prefix="/v1")
