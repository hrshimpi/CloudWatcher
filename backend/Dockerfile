# syntax=docker/dockerfile:1

# ---- builder: resolve dependencies with Poetry, using the committed lock file ----
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.3 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN pip install "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-ansi

# ---- runtime: copy just the venv + app code, run as non-root ----
FROM python:3.11-slim AS runtime

RUN useradd --create-home --uid 1000 appuser
WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}"

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

USER appuser

# Cloud Run injects $PORT (defaults to 8080); fall back to 8080 for `docker run`.
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
