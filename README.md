# Aeris API (FastAPI + SQLAlchemy + Aiven MySQL)

Implements:
- `GET /healthz`
- `POST /v1/readings` (API key + idempotency)
- `GET /v1/devices/{device_id}/readings`

OpenAPI docs: `/docs`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` with your Aiven details and the CA path.

## Run
```bash
uvicorn app.main:app --reload --port 8000
```

See README in chat message for curl tests.
