"""Fuel stations + vehicle range (F20) against Postgres. Skipped without TEST_DATABASE_URL."""

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from routeopt.core.security import hash_password
from routeopt.database import get_session
from routeopt.main import app
from routeopt.models import Base
from routeopt.models.company import Company
from routeopt.models.user import User

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB_URL, reason="TEST_DATABASE_URL not set")


@pytest_asyncio.fixture
async def ctx():
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
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, sessionmaker
    app.dependency_overrides.clear()
    await engine.dispose()


async def _seed(sessionmaker) -> None:
    async with sessionmaker() as s:
        company = Company(name="Acme", plan="pro", max_vehicles=20, max_deliveries_per_day=500)
        s.add(company)
        await s.flush()
        s.add_all(
            [
                User(
                    company_id=company.id,
                    email="khaled@acme.dz",
                    password_hash=hash_password("supersecret"),
                    full_name="Khaled",
                    role="manager",
                ),
                User(
                    company_id=company.id,
                    email="driver@acme.dz",
                    password_hash=hash_password("supersecret"),
                    full_name="Amine",
                    role="driver",
                ),
            ]
        )
        await s.commit()


async def _login(client: AsyncClient, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_fuel_station_crud_and_status(ctx) -> None:
    client, sessionmaker = ctx
    await _seed(sessionmaker)
    manager = await _login(client, "khaled@acme.dz")

    created = await client.post(
        "/api/v1/fuel/stations",
        headers=manager,
        json={
            "name": "Naftal Bab Ezzouar",
            "location": {"lat": 36.72, "lon": 3.18},
            "fuel_types": "essence,diesel",
        },
    )
    assert created.status_code == 201, created.text
    station_id = created.json()["id"]
    assert created.json()["status"] == "available"

    # Flag a shortage.
    upd = await client.put(
        f"/api/v1/fuel/stations/{station_id}/status",
        headers=manager,
        json={"status": "shortage"},
    )
    assert upd.status_code == 200, upd.text
    assert upd.json()["status"] == "shortage"

    listed = await client.get("/api/v1/fuel/stations", headers=manager)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    deleted = await client.delete(f"/api/v1/fuel/stations/{station_id}", headers=manager)
    assert deleted.status_code == 204
    assert (await client.get("/api/v1/fuel/stations", headers=manager)).json() == []


async def test_driver_cannot_manage_stations(ctx) -> None:
    client, sessionmaker = ctx
    await _seed(sessionmaker)
    driver = await _login(client, "driver@acme.dz")
    resp = await client.post(
        "/api/v1/fuel/stations",
        headers=driver,
        json={"name": "X", "location": {"lat": 36.7, "lon": 3.1}},
    )
    assert resp.status_code == 401


async def test_vehicle_carries_fuel_range(ctx) -> None:
    client, sessionmaker = ctx
    await _seed(sessionmaker)
    manager = await _login(client, "khaled@acme.dz")
    resp = await client.post(
        "/api/v1/fleet/vehicles",
        headers=manager,
        json={
            "name": "Fourgon 1",
            "vehicle_type": "van",
            "fuel_range_km": 120,
            "fuel_type": "diesel",
            "depot": {"lat": 36.75, "lon": 3.05},
            "depot_address": "Dépôt",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["fuel_range_km"] == 120
    assert resp.json()["fuel_type"] == "diesel"
