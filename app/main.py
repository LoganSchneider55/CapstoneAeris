from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import readings, devices
from .database import check_db

app = FastAPI(title="Aeris API", version="0.2.0")

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://aeris-one.vercel.app",  # Vercel production dashboard
        # add preview URLs here if you want them to work too, e.g.:
        # "https://aeris-one-git-main-<your-user>.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],   # GET, POST, PATCH, OPTIONS, etc.
    allow_headers=["*"],   # Authorization, Content-Type, etc.
)

@app.get("/healthz")
def healthz():
    ok, msg = check_db()
    return {"status": "ok" if ok else "error", "db": msg}

app.include_router(readings.router, prefix="/v1")
app.include_router(devices.router,  prefix="/v1")
