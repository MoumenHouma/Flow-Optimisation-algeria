"""End-to-end auth flow against a real Postgres.

Skipped unless TEST_DATABASE_URL is set (e.g. the docker-compose postgres):

    TEST_DATABASE_URL=postgresql+asyncpg://routeopt:routeopt@localhost:5432/routeopt \
        pytest tests/test_auth_flow.py

Uses Base.metadata.create_all — the generated `deliveries.geog` column is managed
by the Alembic migration, not the ORM, so it is absent here (and unneeded for auth).
"""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from routeopt.database import get_session
from routeopt.main import app
from routeopt.models import Base

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB_URL, reason="TEST_DATABASE_URL not set")


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await engine.dispose()


async def test_register_login_refresh_me(client: AsyncClient) -> None:
    # Register -> tokens
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Acme Logistics",
            "email": "khaled@acme.dz",
            "password": "supersecret",
            "full_name": "Khaled",
        },
    )
    assert reg.status_code == 201, reg.text
    tokens = reg.json()
    assert tokens["access_token"] and tokens["refresh_token"]

    # Duplicate email -> 409
    dup = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Acme 2",
            "email": "khaled@acme.dz",
            "password": "supersecret",
            "full_name": "Khaled",
        },
    )
    assert dup.status_code == 409

    # /me with access token
    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["role"] == "admin"

    # Login
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "khaled@acme.dz", "password": "supersecret"},
    )
    assert login.status_code == 200

    # Refresh rotates the token; the old one is now revoked
    old_refresh = login.json()["refresh_token"]
    refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert refreshed.status_code == 200
    reused = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401  # single-use enforced


async def test_refresh_reuse_revokes_whole_family(client: AsyncClient) -> None:
    """M3: replaying a rotated token revokes every descendant in its family."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Acme",
            "email": "fam@acme.dz",
            "password": "supersecret",
            "full_name": "Fam",
        },
    )
    r0 = reg.json()["refresh_token"]
    # r0 -> r1 (r0 now revoked, r1 valid and in the same family).
    rotated = await client.post("/api/v1/auth/refresh", json={"refresh_token": r0})
    r1 = rotated.json()["refresh_token"]

    # Replaying r0 is reuse: detected + whole family revoked.
    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": r0})
    assert reuse.status_code == 401

    # r1 was valid before, but the family revocation now kills it too.
    after = await client.post("/api/v1/auth/refresh", json={"refresh_token": r1})
    assert after.status_code == 401


async def test_logout_revokes_refresh_token(client: AsyncClient) -> None:
    """M3: logout revokes the presented refresh token (idempotent, always 204)."""
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Acme",
            "email": "out@acme.dz",
            "password": "supersecret",
            "full_name": "Out",
        },
    )
    refresh_token = reg.json()["refresh_token"]

    out = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert out.status_code == 204
    # The revoked token can no longer be exchanged.
    denied = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert denied.status_code == 401
    # Logout is idempotent — a second call (or an unknown token) still 204s.
    again = await client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert again.status_code == 204
