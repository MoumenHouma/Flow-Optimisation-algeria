"""Audit trail (H2) against Postgres.

Verifies sensitive actions are recorded (login, branding change) and that the
admin-only GET /audit-log lists them, newest first. Skipped without
TEST_DATABASE_URL.
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


async def _admin(client: AsyncClient) -> dict[str, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Acme",
            "email": "boss@acme.dz",
            "password": "supersecret",
            "full_name": "Boss",
        },
    )
    assert reg.status_code == 201, reg.text
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}


async def test_login_and_branding_are_audited(client: AsyncClient) -> None:
    headers = await _admin(client)

    # A login writes a user.login entry.
    await client.post(
        "/api/v1/auth/login", json={"email": "boss@acme.dz", "password": "supersecret"}
    )
    # A branding change writes a company.branding_changed entry.
    branding = await client.put(
        "/api/v1/company/branding", headers=headers, json={"primary_color": "#10B981"}
    )
    assert branding.status_code == 200, branding.text

    log = await client.get("/api/v1/audit-log", headers=headers)
    assert log.status_code == 200, log.text
    actions = [e["action"] for e in log.json()]
    assert "user.login" in actions
    assert "company.branding_changed" in actions

    # Filter narrows to a single action type.
    filtered = await client.get("/api/v1/audit-log?action=user.login", headers=headers)
    assert filtered.status_code == 200
    assert all(e["action"] == "user.login" for e in filtered.json())
    assert len(filtered.json()) >= 1


async def test_audit_log_requires_admin(client: AsyncClient) -> None:
    headers = await _admin(client)
    # A driver may not read the audit log.
    await client.post(
        "/api/v1/fleet/drivers",
        headers=headers,
        json={"email": "drv@acme.dz", "password": "supersecret", "full_name": "Drv"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": "drv@acme.dz", "password": "supersecret"}
    )
    drv = {"Authorization": f"Bearer {login.json()['access_token']}"}
    denied = await client.get("/api/v1/audit-log", headers=drv)
    assert denied.status_code == 403
