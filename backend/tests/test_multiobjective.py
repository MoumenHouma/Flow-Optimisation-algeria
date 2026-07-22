"""Multi-objective optimization payload + result (F14) against Postgres + fakeredis.

Verifies the optimize request carries objective weights + per-vehicle type, and
that the worker's fuel/CO2 breakdown round-trips onto the job. Skipped without
TEST_DATABASE_URL.
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
        yield ac, fake_redis
    app.dependency_overrides.clear()
    await engine.dispose()


async def _auth(client: AsyncClient) -> dict[str, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Acme",
            "email": "k@acme.dz",
            "password": "supersecret",
            "full_name": "K",
        },
    )
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}


async def test_objective_and_vehicle_type_in_payload_and_result(client) -> None:
    ac, fake_redis = client
    headers = await _auth(ac)

    await ac.post(
        "/api/v1/fleet/vehicles",
        headers=headers,
        json={
            "name": "Fourgon",
            "vehicle_type": "van",
            "capacity_weight": 500,
            "depot": {"lat": 36.7538, "lon": 3.0588},
            "depot_address": "Dépôt",
        },
    )
    orders = await ac.post(
        "/api/v1/orders",
        headers=headers,
        json=[{"address": "A", "lat": 36.75, "lon": 3.06, "weight": 5}],
    )
    delivery_ids = [d["id"] for d in orders.json()["deliveries"]]

    # Eco-weighted objective.
    submit = await ac.post(
        "/api/v1/routes/optimize",
        headers=headers,
        json={"objective": {"distance": 0.2, "time": 0.2, "fuel": 3, "co2": 2}},
    )
    assert submit.status_code == 202, submit.text
    job_id = submit.json()["job_id"]

    msg = json.loads((await fake_redis.lrange("queue:optimize", 0, -1))[-1])
    assert msg["objective"] == {"distance": 0.2, "time": 0.2, "fuel": 3.0, "co2": 2.0}
    assert msg["vehicles"][0]["vehicle_type"] == "van"

    # Simulate the worker returning a cost breakdown.
    worker_result = {
        "job_id": job_id,
        "company_id": msg["company_id"],
        "status": "completed",
        "strategy": "or_tools",
        "total_distance_m": 2000,
        "total_time_s": 600,
        "total_fuel_l": 0.18,
        "total_co2_kg": 0.46,
        "routes": [
            {
                "vehicle_id": msg["vehicles"][0]["id"],
                "total_distance_m": 2000,
                "total_time_s": 600,
                "fuel_l": 0.18,
                "co2_kg": 0.46,
                "stops": [{"delivery_id": delivery_ids[0], "sequence": 0}],
            }
        ],
    }
    await fake_redis.set(f"opt:result:{job_id}", json.dumps(worker_result))

    job = await ac.get(f"/api/v1/routes/jobs/{job_id}", headers=headers)
    assert job.status_code == 200, job.text
    body = job.json()
    assert body["total_fuel_l"] == 0.18
    assert body["total_co2_kg"] == 0.46
