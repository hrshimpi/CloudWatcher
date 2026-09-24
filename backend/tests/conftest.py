"""Shared pytest fixtures for DB- and API-backed tests.

Tests run against a dedicated `cloudwatcher_test` database on the same
Postgres server as local dev (same host/port/credentials from `.env`, just a
different database name) -- never against the real `cloudwatcher` dev
database, so running the suite can't wipe out locally seeded demo data.
"""

from __future__ import annotations

import asyncpg
import httpx
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.database import get_db
from app.main import app
from app.models.base import Base

TEST_DB_NAME = "cloudwatcher_test"


def _database_url(dbname: str) -> str:
    settings = get_settings()
    return (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{dbname}"
    )


async def _ensure_test_database_exists() -> None:
    settings = get_settings()
    conn = await asyncpg.connect(
        user=settings.postgres_user,
        password=settings.postgres_password,
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
    )
    try:
        await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    except asyncpg.exceptions.DuplicateDatabaseError:
        pass
    finally:
        await conn.close()


@pytest_asyncio.fixture
async def test_engine():
    # Function-scoped, not session-scoped: pytest-asyncio gives each test
    # function its own event loop by default, and an asyncpg connection pool
    # created under one loop can't be reused from another ("Future attached
    # to a different loop"). A fresh engine per test sidesteps that entirely
    # -- the minor overhead of recreating it each time is negligible here.
    await _ensure_test_database_exists()
    engine = create_async_engine(_database_url(TEST_DB_NAME))

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Isolate each test: clear every table rather than relying on
        # savepoint rollback, which has more edge cases with async sessions.
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    # A plain sync TestClient runs the ASGI app on a separate thread/event
    # loop, which would hand our asyncpg-backed db_session to a different
    # loop than the one it was created on and blow up. httpx.AsyncClient +
    # ASGITransport runs the app in-process on the test's own event loop.
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client

    app.dependency_overrides.clear()
