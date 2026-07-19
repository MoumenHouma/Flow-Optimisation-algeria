"""End-to-end fleet management (F7) against Postgres. Skipped without TEST_DATABASE_URL."""

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


async def _auth(client: AsyncClient) -> dict[str, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Acme",
            "email": "k@acme.dz",
            "password": "supersecret",
            "full_name": "Khaled",
        },
    )
    assert reg.status_code == 201, reg.text
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}


def _vehicle(name: str) -> dict:
    return {
        "name": name,
        "vehicle_type": "van",
        "capacity_weight": 500,
        "depot": {"lat": 36.7538, "lon": 3.0588},
        "depot_address": "Dépôt Alger Centre",
    }


async def test_fleet_lifecycle(client: AsyncClient) -> None:
    headers = await _auth(client)

    # New free-plan company: quota 1 vehicle, none yet
    summary = await client.get("/api/v1/fleet/summary", headers=headers)
    assert summary.json() == {"plan": "free", "vehicle_count": 0, "max_vehicles": 1}

    # Add one
    created = await client.post("/api/v1/fleet/vehicles", headers=headers, json=_vehicle("V1"))
    assert created.status_code == 201, created.text
    vid = created.json()["id"]

    # Free plan caps at 1 -> second add is rejected
    second = await client.post("/api/v1/fleet/vehicles", headers=headers, json=_vehicle("V2"))
    assert second.status_code == 409

    # List shows one
    listed = await client.get("/api/v1/fleet/vehicles", headers=headers)
    assert [v["name"] for v in listed.json()] == ["V1"]

    # Update it
    updated = await client.put(
        f"/api/v1/fleet/vehicles/{vid}",
        headers=headers,
        json={**_vehicle("V1 renamed"), "capacity_weight": 750},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "V1 renamed"
    assert updated.json()["capacity_weight"] == 750

    # Delete (soft) frees the quota slot
    deleted = await client.delete(f"/api/v1/fleet/vehicles/{vid}", headers=headers)
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/fleet/vehicles", headers=headers)).json() == []
    assert (await client.get("/api/v1/fleet/summary", headers=headers)).json()["vehicle_count"] == 0

    # Now a new vehicle fits again
    again = await client.post("/api/v1/fleet/vehicles", headers=headers, json=_vehicle("V3"))
    assert again.status_code == 201

    # Updating a missing vehicle -> 404
    missing = await client.put(
        "/api/v1/fleet/vehicles/00000000-0000-0000-0000-000000000000",
        headers=headers,
        json=_vehicle("ghost"),
    )
    assert missing.status_code == 404
