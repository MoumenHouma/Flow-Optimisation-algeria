"""Dynamic re-optimization (F9) against Postgres + fakeredis.

Flow: optimize a route, mark one stop delivered, POST /routes/{id}/reoptimize,
simulate the worker re-planning the *remaining* stops, then verify the live route
is re-sequenced in place — done stops stay fixed at the front, the rest follow
the worker's new order. Skipped unless TEST_DATABASE_URL is set.
"""

import json
import os
import uuid

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from routeopt.database import get_session
from routeopt.main import app
from routeopt.models import Base
from routeopt.models.delivery import Delivery

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB_URL, reason="TEST_DATABASE_URL not set")


@pytest_asyncio.fixture
async def fake_redis(monkeypatch):
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("routeopt.modules.routes.service.redis_client", client)
    monkeypatch.setattr("routeopt.core.dependencies.redis_client", client)
    return client


@pytest_asyncio.fixture
async def ctx(fake_redis):
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
        yield ac, sessionmaker, fake_redis
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


async def _seed_route(client: AsyncClient, headers, fake_redis) -> tuple[str, list[str]]:
    """Optimize 3 deliveries into one route; return (route_id, [delivery_ids])."""
    await client.post(
        "/api/v1/fleet/vehicles",
        headers=headers,
        json={
            "name": "Camion 1",
            "capacity_weight": 500,
            "depot": {"lat": 36.7538, "lon": 3.0588},
            "depot_address": "Dépôt",
        },
    )
    orders = await client.post(
        "/api/v1/orders",
        headers=headers,
        json=[
            {"address": "A", "lat": 36.75, "lon": 3.06, "weight": 5},
            {"address": "B", "lat": 36.76, "lon": 3.07, "weight": 8},
            {"address": "C", "lat": 36.77, "lon": 3.08, "weight": 3},
        ],
    )
    delivery_ids = [d["id"] for d in orders.json()["deliveries"]]

    submit = await client.post("/api/v1/routes/optimize", headers=headers, json={})
    job_id = submit.json()["job_id"]
    msg = json.loads((await fake_redis.lrange("queue:optimize", 0, -1))[-1])
    worker_result = {
        "job_id": job_id,
        "company_id": msg["company_id"],
        "status": "completed",
        "strategy": "or_tools",
        "total_distance_m": 3000,
        "routes": [
            {
                "vehicle_id": msg["vehicles"][0]["id"],
                "total_distance_m": 3000,
                "total_time_s": 900,
                "stops": [{"delivery_id": delivery_ids[i], "sequence": i} for i in range(3)],
            }
        ],
    }
    await fake_redis.set(f"opt:result:{job_id}", json.dumps(worker_result))
    job = await client.get(f"/api/v1/routes/jobs/{job_id}", headers=headers)
    return job.json()["route_ids"][0], delivery_ids


async def _mark(sessionmaker, delivery_id: str, status: str) -> None:
    async with sessionmaker() as s:
        d = await s.get(Delivery, uuid.UUID(delivery_id))
        d.status = status
        await s.commit()


async def test_reoptimize_resequences_remaining_stops(ctx) -> None:
    client, sessionmaker, fake_redis = ctx
    headers = await _auth(client)
    route_id, dids = await _seed_route(client, headers, fake_redis)

    # First stop is delivered; the other two remain.
    await _mark(sessionmaker, dids[0], "delivered")

    resp = await client.post(
        f"/api/v1/routes/{route_id}/reoptimize",
        headers=headers,
        json={"current_lat": 36.75, "current_lon": 3.06},
    )
    assert resp.status_code == 202, resp.text
    job_id = resp.json()["job_id"]

    # The enqueued job covers only the two remaining stops, from the driver position.
    msg = json.loads((await fake_redis.lrange("queue:optimize", 0, -1))[-1])
    assert msg["job_id"] == job_id
    assert {d["id"] for d in msg["deliveries"]} == {dids[1], dids[2]}
    assert msg["depot"] == {"lat": 36.75, "lon": 3.06}
    assert len(msg["vehicles"]) == 1

    # Worker re-plans the remaining pair in reversed order.
    worker_result = {
        "job_id": job_id,
        "company_id": msg["company_id"],
        "status": "completed",
        "strategy": "or_tools",
        "total_distance_m": 1500,
        "routes": [
            {
                "vehicle_id": msg["vehicles"][0]["id"],
                "total_distance_m": 1500,
                "total_time_s": 500,
                "stops": [
                    {"delivery_id": dids[2], "sequence": 0},
                    {"delivery_id": dids[1], "sequence": 1},
                ],
            }
        ],
    }
    await fake_redis.set(f"opt:result:{job_id}", json.dumps(worker_result))

    job = await client.get(f"/api/v1/routes/jobs/{job_id}", headers=headers)
    assert job.json()["status"] == "completed"

    # Route re-sequenced in place: delivered stop stays first, then the new order.
    route = await client.get(f"/api/v1/routes/{route_id}", headers=headers)
    ordered = sorted(route.json()["stops"], key=lambda s: s["sequence"])
    assert [s["delivery_id"] for s in ordered] == [dids[0], dids[2], dids[1]]
    assert route.json()["total_distance_m"] == 1500


async def test_reoptimize_without_remaining_is_rejected(ctx) -> None:
    client, sessionmaker, fake_redis = ctx
    headers = await _auth(client)
    route_id, dids = await _seed_route(client, headers, fake_redis)
    for d in dids:
        await _mark(sessionmaker, d, "delivered")

    resp = await client.post(f"/api/v1/routes/{route_id}/reoptimize", headers=headers, json={})
    assert resp.status_code == 422


async def test_reoptimize_unknown_route_404(ctx) -> None:
    client, _, _ = ctx
    headers = await _auth(client)
    resp = await client.post(f"/api/v1/routes/{uuid.uuid4()}/reoptimize", headers=headers, json={})
    assert resp.status_code == 404
