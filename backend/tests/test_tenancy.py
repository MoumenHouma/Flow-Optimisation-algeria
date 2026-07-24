"""Cross-tenant isolation (Batch 1 / M2) against Postgres."""

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


async def _register(client: AsyncClient, company: str, email: str) -> dict[str, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={"company_name": company, "email": email, "password": "supersecret", "full_name": "X"},
    )
    assert reg.status_code == 201, reg.text
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}


async def test_cannot_assign_foreign_driver_to_vehicle(client) -> None:
    a = await _register(client, "Acme", "a@acme.dz")
    b = await _register(client, "Beta", "b@beta.dz")

    # A driver belonging to company B.
    drv = await client.post(
        "/api/v1/fleet/drivers",
        headers=b,
        json={"email": "drvB@beta.dz", "password": "supersecret", "full_name": "Driver B"},
    )
    foreign_driver_id = drv.json()["id"]

    # Company A tries to assign B's driver to its vehicle → rejected (422), not a leak.
    resp = await client.post(
        "/api/v1/fleet/vehicles",
        headers=a,
        json={
            "name": "Camion A",
            "capacity_weight": 500,
            "depot": {"lat": 36.75, "lon": 3.05},
            "depot_address": "Dépôt",
            "driver_user_id": foreign_driver_id,
        },
    )
    assert resp.status_code == 422


async def test_cannot_assign_foreign_driver_to_territory(client) -> None:
    a = await _register(client, "Acme", "a2@acme.dz")
    b = await _register(client, "Beta", "b2@beta.dz")
    drv = await client.post(
        "/api/v1/fleet/drivers",
        headers=b,
        json={"email": "drvB2@beta.dz", "password": "supersecret", "full_name": "Driver B"},
    )
    resp = await client.post(
        "/api/v1/territories",
        headers=a,
        json={"name": "Zone", "color": "#2563EB", "driver_user_id": drv.json()["id"]},
    )
    assert resp.status_code == 422
