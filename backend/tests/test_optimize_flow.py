"""End-to-end optimize flow against Postgres + fakeredis.

Exercises the full API path: register -> add vehicle -> add deliveries ->
POST /optimize (enqueues to Redis) -> simulate the worker writing a result ->
GET /jobs/{id} (lazy-persists) -> GET /routes/{id}.

The worker's compute is covered in the optimization-worker package; here we feed
a worker-shaped result message to verify the backend contract + persistence.

Skipped unless TEST_DATABASE_URL is set.
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
    # Both submit (enqueue) and get_job (result read) use this module-level client.
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


async def test_full_optimize_flow(client: AsyncClient, fake_redis) -> None:
    headers = await _auth(client)

    # Seed a vehicle
    veh = await client.post(
        "/api/v1/fleet/vehicles",
        headers=headers,
        json={
            "name": "Camion 1",
            "capacity_weight": 500,
            "depot": {"lat": 36.7538, "lon": 3.0588},
            "depot_address": "Dépôt Alger Centre",
        },
    )
    assert veh.status_code == 201, veh.text

    # Seed deliveries (with coords -> ready to route)
    orders = await client.post(
        "/api/v1/orders",
        headers=headers,
        json=[
            {"address": "12 Rue Didouche Mourad", "lat": 36.75, "lon": 3.06, "weight": 5},
            {"address": "45 Bd Mohamed V", "lat": 36.76, "lon": 3.07, "weight": 8},
        ],
    )
    assert orders.status_code == 201, orders.text
    delivery_ids = [d["id"] for d in orders.json()["deliveries"]]

    # Submit optimization (empty ids => all routable / all active vehicles)
    submit = await client.post("/api/v1/routes/optimize", headers=headers, json={})
    assert submit.status_code == 202, submit.text
    job_id = submit.json()["job_id"]
    assert submit.json()["status"] == "pending"

    # A message was enqueued for the worker
    queued = await fake_redis.lrange("queue:optimize", 0, -1)
    assert len(queued) == 1
    msg = json.loads(queued[0])
    assert msg["job_id"] == job_id
    assert len(msg["deliveries"]) == 2 and len(msg["vehicles"]) == 1

    # Simulate the worker: produce a result and publish it to Redis
    worker_result = {
        "job_id": job_id,
        "company_id": msg["company_id"],
        "status": "completed",
        "strategy": "or_tools",
        "used_osrm": False,
        "is_suboptimal": True,
        "duration_ms": 42,
        "total_distance_m": 1234.5,
        "total_time_s": 300,
        "objective_value": 1234,
        "routes": [
            {
                "vehicle_id": msg["vehicles"][0]["id"],
                "total_distance_m": 1234.5,
                "total_time_s": 300,
                "stops": [
                    {"delivery_id": delivery_ids[0], "sequence": 0, "eta_s": 0},
                    {"delivery_id": delivery_ids[1], "sequence": 1, "eta_s": 600},
                ],
            }
        ],
    }
    await fake_redis.set(f"opt:result:{job_id}", json.dumps(worker_result))

    # Poll -> lazy-persists the result
    job = await client.get(f"/api/v1/routes/jobs/{job_id}", headers=headers)
    assert job.status_code == 200, job.text
    body = job.json()
    assert body["status"] == "completed"
    assert body["total_distance_m"] == 1234.5
    assert len(body["route_ids"]) == 1

    # Fetch the route with its ordered stops
    route = await client.get(f"/api/v1/routes/{body['route_ids'][0]}", headers=headers)
    assert route.status_code == 200, route.text
    route_body = route.json()
    stops = route_body["stops"]
    assert [s["sequence"] for s in stops] == [0, 1]
    assert {s["delivery_id"] for s in stops} == set(delivery_ids)
    # Enriched for the map: each stop carries coordinates + the route has a depot
    assert all(s["lat"] is not None and s["lon"] is not None for s in stops)
    assert route_body["depot"] == {"lat": 36.7538, "lon": 3.0588}

    # Deliveries are no longer routable (now assigned to the route)
    routable = await client.get("/api/v1/orders", headers=headers)
    assert routable.json() == []

    # Second poll is idempotent — no duplicate routes created
    job2 = await client.get(f"/api/v1/routes/jobs/{job_id}", headers=headers)
    assert len(job2.json()["route_ids"]) == 1
