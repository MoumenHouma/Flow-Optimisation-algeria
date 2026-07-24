"""Multi-dépôt (F12) against Postgres + fakeredis.

Covers depot CRUD, resolving a vehicle's departure point from a depot, and the
optimize payload carrying each vehicle's own depot (what the multi-depot solver
consumes). Skipped without TEST_DATABASE_URL.
"""

import json
import os

import fakeredis.aioredis
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
async def fake_redis(monkeypatch):
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("routeopt.modules.routes.service.redis_client", client)
    monkeypatch.setattr("routeopt.core.dependencies.redis_client", client)
    return client


@pytest_asyncio.fixture
async def client(fake_redis):
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
        yield ac, fake_redis, sessionmaker
    app.dependency_overrides.clear()
    await engine.dispose()


async def _raise_vehicle_quota(sessionmaker) -> None:
    """Lift the free-plan 1-vehicle cap so multi-vehicle scenarios can be seeded."""
    from sqlalchemy import select

    from routeopt.models.company import Company

    async with sessionmaker() as s:
        company = (await s.scalars(select(Company))).first()
        company.max_vehicles = None
        await s.commit()


async def _auth(client: AsyncClient) -> dict[str, str]:
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


async def _depot(client, headers, name, lat, lon) -> str:
    resp = await client.post(
        "/api/v1/fleet/depots",
        headers=headers,
        json={"name": name, "location": {"lat": lat, "lon": lon}, "address": f"{name} addr"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_depot_crud(client) -> None:
    ac, _, _ = client
    headers = await _auth(ac)

    depot_id = await _depot(ac, headers, "Entrepôt Alger", 36.7538, 3.0588)
    listed = await ac.get("/api/v1/fleet/depots", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["location"] == {"lat": 36.7538, "lon": 3.0588}

    upd = await ac.put(
        f"/api/v1/fleet/depots/{depot_id}",
        headers=headers,
        json={"name": "Entrepôt Oran", "location": {"lat": 35.69, "lon": -0.63}, "address": "Oran"},
    )
    assert upd.status_code == 200
    assert upd.json()["name"] == "Entrepôt Oran"

    rem = await ac.delete(f"/api/v1/fleet/depots/{depot_id}", headers=headers)
    assert rem.status_code == 204
    assert (await ac.get("/api/v1/fleet/depots", headers=headers)).json() == []


async def test_vehicle_resolves_depot_from_id(client) -> None:
    ac, _, _ = client
    headers = await _auth(ac)
    depot_id = await _depot(ac, headers, "Central", 36.75, 3.05)

    veh = await ac.post(
        "/api/v1/fleet/vehicles",
        headers=headers,
        json={"name": "Camion 1", "capacity_weight": 500, "depot_id": depot_id},
    )
    assert veh.status_code == 201, veh.text
    body = veh.json()
    assert body["depot_id"] == depot_id
    # Coordinates + address are resolved from the depot.
    assert body["depot"] == {"lat": 36.75, "lon": 3.05}
    assert body["depot_address"] == "Central addr"


async def test_vehicle_requires_depot_or_inline(client) -> None:
    ac, _, _ = client
    headers = await _auth(ac)
    resp = await ac.post(
        "/api/v1/fleet/vehicles",
        headers=headers,
        json={"name": "No depot", "capacity_weight": 500},
    )
    assert resp.status_code == 422


async def test_optimize_sends_per_vehicle_depots(client) -> None:
    ac, fake_redis, sessionmaker = client
    headers = await _auth(ac)
    await _raise_vehicle_quota(sessionmaker)
    depot_a = await _depot(ac, headers, "A", 36.75, 3.05)
    depot_b = await _depot(ac, headers, "B", 36.80, 3.20)

    for name, depot_id in [("VA", depot_a), ("VB", depot_b)]:
        veh = await ac.post(
            "/api/v1/fleet/vehicles",
            headers=headers,
            json={"name": name, "capacity_weight": 500, "depot_id": depot_id},
        )
        assert veh.status_code == 201, veh.text

    orders = await ac.post(
        "/api/v1/orders",
        headers=headers,
        json=[
            {"address": "near A", "lat": 36.75, "lon": 3.06, "weight": 5},
            {"address": "near B", "lat": 36.80, "lon": 3.21, "weight": 5},
        ],
    )
    assert orders.status_code == 201, orders.text

    submit = await ac.post("/api/v1/routes/optimize", headers=headers, json={})
    assert submit.status_code == 202, submit.text

    msg = json.loads((await fake_redis.lrange("queue:optimize", 0, -1))[-1])
    depots = {(v["depot"]["lat"], v["depot"]["lon"]) for v in msg["vehicles"]}
    # Each vehicle carries its own depot — the multi-depot solver keys off these.
    assert depots == {(36.75, 3.05), (36.80, 3.20)}
