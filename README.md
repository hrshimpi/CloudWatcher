# CloudWatcher

A cloud cost monitoring service: ingests daily cloud billing data, tracks per-service spend, flags anomalies (unexpected cost spikes), and alerts on them. FastAPI backend backed by Postgres, React dashboard frontend.

## Stack

- **Backend**: FastAPI, SQLAlchemy 2.0 (async), Alembic, Postgres 15
- **Frontend**: React, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router, Recharts
- **Infra**: Docker Compose for local dev; Terraform + GitHub Actions for GCP (Cloud Run, Cloud SQL, Secret Manager, Cloud Scheduler) — see [Deployment](#deployment)

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
    api/        # typed fetch client
    components/ # TopNav, KpiRow, CostTrendChart, AnomaliesTable
    context/    # shared provider/date-range filter state
    pages/      # Dashboard, ServiceDrilldown, Settings
docker-compose.yml
```

## Data model

- `billing_records` — raw per-SKU line items (provider, account, service, SKU, date, cost)
- `daily_service_costs` — daily cost rolled up per provider/service
- `anomalies` — flagged cost anomalies (expected vs. actual, z-score, root cause)
- `alert_config` — per-service (or global, when `service` is null) alert thresholds and Slack webhook

## API

| Endpoint | Description |
| --- | --- |
| `GET /costs/summary` | Total cost + per-service breakdown + daily trend. Filter with `provider`, `start_date`, `end_date`. |
| `GET /anomalies` | List flagged anomalies. Filter with `status`, `service`, `start_date`, `end_date`; paginate with `limit`/`offset`. |
| `GET /anomalies/{id}` | A single anomaly. |
| `GET /services/{service}/drilldown` | Daily time series + top-N contributing SKUs for one service. Filter with `start_date`, `end_date`, `top_n`. |
| `GET /config/thresholds` | List alert configs (per-service + the global default where `service` is null). Filter with `service`. |
| `PUT /config/thresholds` | Create or update the alert config for a `service` (or the global default, when omitted). |
| `POST /alerts/test` | Send a test Slack message. See [Slack alerting](#slack-alerting). |
| `POST /anomalies/detect` | Run detection for every service and alert on anything newly flagged. What Cloud Scheduler calls nightly in production; safe to call manually (`?dry_run=true` to preview). |

All responses are JSON; request/response shapes are defined in `app/schemas/`. Interactive docs are at `http://localhost:8000/docs` once the backend is running.

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

Runs on `http://localhost:5173`, proxying `/api/*` requests to the backend at `http://localhost:8000` (stripping the `/api` prefix — see `vite.config.ts`).

- **Dashboard** (`/`) — a top nav with provider and date-range filters, a KPI row (total spend, change vs. the previous period, active anomalies, biggest spike), a cost trend chart with anomaly days marked, and an anomalies table whose rows expand to show the root-cause explanation.
- **Service drilldown** (`/services/:service`) — that service's own cost trend plus its top contributing SKUs, over the same date range.
- **Settings** (`/settings`) — the global Slack webhook URL and Z-score threshold, backed by `GET`/`PUT /config/thresholds`.

All data fetching goes through TanStack Query (`src/api/client.ts`); there's no separate state-management layer beyond the shared provider/date-range filters in `src/context/FiltersContext.tsx`.

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

Run the test suite:

```bash
cd backend
poetry run pytest
```

Needs Postgres reachable (same connection info as `.env`) — the API and DB-backed tests run against a separate `cloudwatcher_test` database on that same server, created automatically on first run, so they never touch your local dev/demo data. The anomaly-detection tests use the synthetic generator above to confirm injected spikes are caught and the weekly BigQuery pattern isn't.

### Slack alerting

`app/services/alerting.py` sends a Slack message for each newly flagged anomaly. It asks an LLM (Gemini, via `GEMINI_API_KEY`) for a one-sentence plain-English root-cause guess based on the service, cost delta, % deviation, and top-contributing SKU; on success that replaces the anomaly's templated explanation, and either way the message posts to the webhook configured in `alert_config` (per-service, or the global default row where `service` is null). If the LLM call fails, times out, or no key is set, it silently falls back to the templated explanation — the alert always sends regardless.

```python
from app.services.alerting import detect_and_alert

results = await detect_and_alert(session)  # detect anomalies, then alert on each one
```

`ALERTS_DRY_RUN=true` (the default) logs the message instead of posting it — flip it to `false` once a real webhook is set. Send a one-off test message without waiting for a real anomaly:

```bash
curl -X POST http://localhost:8000/alerts/test \
  -H "Content-Type: application/json" \
  -d '{"service": "BigQuery", "slack_webhook_url": "https://hooks.slack.com/services/...", "dry_run": true}'
```

`slack_webhook_url` is optional — omit it to use whatever's configured in `alert_config` for that service (or the global default).

### Docker Compose

Spins up Postgres and the backend together:

```bash
docker compose up --build
```

Postgres is published on host port `5434` (mapped to `5432` in the container) to avoid clashing with a locally installed Postgres. The backend container listens on `8080` internally (matching Cloud Run's convention — see Deployment below) and is published on host port `8000`, so `http://localhost:8000` works the same as running it directly with Poetry.

## Environment variables

See `backend/.env.example` for the variables the backend reads (Postgres connection details, app name, environment).

## Deployment

`backend/Dockerfile` and `frontend/Dockerfile` build production images: the backend as a multi-stage Poetry build running as a non-root user, the frontend as a static Vite build served by nginx, which also reverse-proxies `/api/*` to the backend's URL at runtime (so the browser only ever talks to one origin, and the backend never needs CORS configured — see `frontend/nginx.conf.template`).

`infra/` has Terraform for the GCP side: two Cloud Run services (`api`, `frontend`), Cloud SQL Postgres (connected via Cloud Run's built-in Cloud SQL Auth Proxy integration), Secret Manager entries for the Slack webhook and Gemini API key, a nightly Cloud Scheduler job hitting `POST /anomalies/detect`, an Artifact Registry repo, and the IAM to wire it together — including Workload Identity Federation so GitHub Actions never holds a service account key. See `infra/README.md` for the one-time bootstrap steps (state bucket, first manual apply, repo secrets).

`.github/workflows/ci-cd.yml` runs backend (pytest + ruff) and frontend (build + lint) checks plus `terraform validate` on every PR and push; on a push to `main`, once those pass, it builds and pushes both images to Artifact Registry, runs `alembic upgrade head` against Cloud SQL through the Auth Proxy, and applies the Terraform to roll the new images out to Cloud Run.
