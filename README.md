# CloudWatcher

A cloud cost monitoring service: ingests daily cloud billing data, tracks per-service spend, and flags anomalies (unexpected cost spikes) for alerting. FastAPI backend backed by Postgres, React/Vite frontend.

## Stack

- **Backend**: FastAPI, SQLAlchemy 2.0 (async), Alembic, Postgres 15
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **Infra**: Docker Compose for local Postgres + backend

## Project structure

```
backend/
  app/
    api/        # route handlers
    cli/        # CLI entry points (e.g. DB seeding)
    core/       # config, db session
    models/     # SQLAlchemy models
    services/   # business logic
  alembic/      # migrations
frontend/
  src/
docker-compose.yml
```

## Data model

- `billing_records` — raw per-SKU line items (provider, account, service, SKU, date, cost)
- `daily_service_costs` — daily cost rolled up per provider/service
- `anomalies` — flagged cost anomalies (expected vs. actual, z-score, root cause)
- `alert_config` — per-service (or global, when `service` is null) alert thresholds and Slack webhook

## Running locally

### Backend

Requires Python 3.11 and [Poetry](https://python-poetry.org/).

```bash
cd backend
poetry install
cp .env.example .env
poetry run uvicorn app.main:app --reload
```

The API comes up on `http://localhost:8000`. `/health` checks that a Postgres connection can be established.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Runs on `http://localhost:5173`, proxying `/api` requests to the backend.

### Database migrations

```bash
cd backend
poetry run alembic revision --autogenerate -m "message"
poetry run alembic upgrade head
```

### Seeding sample data

There's no live GCP billing export wired up yet, so `seed-db` generates a synthetic dataset instead: 90 days of daily costs across 8 GCP services, with normal day-to-day noise, a recurring weekly pattern on one service (BigQuery runs ~3x heavier every Monday, simulating a batch job — this should be treated as expected, not anomalous), and a few random one-off cost spikes injected as genuine anomalies.

```bash
cd backend
poetry run seed-db              # 90 days, truncates existing billing data first
poetry run seed-db --days 30    # shorter window
poetry run seed-db --append     # don't truncate first
```

The command prints which (service, date) pairs it injected as spikes, so you can check that anomaly detection actually catches them.

### Anomaly detection

`app/services/anomaly_detection.py` decomposes each service's daily cost history with STL (weekly seasonality) into trend, seasonal, and residual components, then flags a day when its residual is more than 2.5 standard deviations (configurable) from the trailing 30-day residual mean. Services with under 21 days of history are skipped rather than flagged — STL needs more warm-up than a plain rolling average would. Flagged days get their top-contributing SKU looked up and a plain-text explanation, then get written to the `anomalies` table.

```python
from app.services.anomaly_detection import detect_and_record_anomalies

anomalies = await detect_and_record_anomalies(session)  # checks "today" for every service
```

Run the test suite (uses the synthetic generator above to confirm injected spikes are caught and the weekly BigQuery pattern isn't):

```bash
cd backend
poetry run pytest
```

### Docker Compose

Spins up Postgres and the backend together:

```bash
docker compose up --build
```

Postgres is published on host port `5434` (mapped to `5432` in the container) to avoid clashing with a locally installed Postgres.

## Environment variables

See `backend/.env.example` for the variables the backend reads (Postgres connection details, app name, environment).
