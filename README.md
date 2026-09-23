# CloudWatcher

A small full-stack service for tracking system health. FastAPI backend backed by Postgres, React/Vite frontend.

## Stack

- **Backend**: FastAPI, SQLAlchemy 2.0 (async), Alembic, Postgres 15
- **Frontend**: React, TypeScript, Vite, Tailwind CSS
- **Infra**: Docker Compose for local Postgres + backend

## Project structure

```
backend/
  app/
    api/        # route handlers
    core/       # config, db session
    models/     # SQLAlchemy models
    services/   # business logic
  alembic/      # migrations
frontend/
  src/
docker-compose.yml
```

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

### Docker Compose

Spins up Postgres and the backend together:

```bash
docker compose up --build
```

## Environment variables

See `backend/.env.example` for the variables the backend reads (Postgres connection details, app name, environment).
