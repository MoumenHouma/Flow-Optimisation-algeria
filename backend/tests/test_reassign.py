"""Blocked-vehicle replan (F20) against Postgres + fakeredis. Skipped without TEST_DATABASE_URL.

A blocked vehicle's route is retired, its undelivered stops are detached and a
fresh multi-vehicle job (trigger='reassign') is enqueued over the rest of the fleet.
"""

import json
import os
import uuid
from datetime import UTC, datetime

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from routeopt.core.security import hash_password
from routeopt.database import get_session
from routeopt.main import app
from routeopt.models import Base
from routeopt.models.company import Company
from routeopt.models.delivery import Delivery
from routeopt.models.optimization_job import OptimizationJob
from routeopt.models.route import Route, RouteStop
from routeopt.models.user import User
from routeopt.models.vehicle import Vehicle

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB_URL, reason="TEST_DATABASE_URL not set")


@pytest_asyncio.fixture
async def fake_redis(monkeypatch):
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    for mod in ("routeopt.core.dependencies", "routeopt.modules.routes.service"):
        monkeypatch.setattr(f"{mod}.redis_client", client)
    return client


@pytest_asyncio.fixture
async def ctx(fake_redis):
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session():
        async with sm() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, sm, fake_redis
    app.dependency_overrides.clear()
    await engine.dispose()


async def _seed(sm):
    """One company + manager, a blocked vehicle A on a route with 2 stops, and a
    free vehicle B to take them over."""
    async with sm() as s:
        company = Company(name="Acme", max_vehicles=None, max_deliveries_per_day=None)
        s.add(company)
        await s.flush()
        s.add(
            User(
                company_id=company.id,
                email="khaled@acme.dz",
                password_hash=hash_password("supersecret"),
                full_name="Khaled",
                role="manager",
            )
        )
        va = Vehicle(
            company_id=company.id, name="A", depot_lat=36.75, depot_lon=3.05, depot_address="Dépôt"
        )
        vb = Vehicle(
            company_id=company.id, name="B", depot_lat=36.76, depot_lon=3.06, depot_address="Dépôt"
        )
        s.add_all([va, vb])
        await s.flush()
        route = Route(company_id=company.id, vehicle_id=va.id, status="in_progress")
        s.add(route)
        await s.flush()
        d1 = Delivery(
            company_id=company.id,
            route_id=route.id,
            address="A",
            lat=36.75,
            lon=3.06,
            status="assigned",
        )
        d2 = Delivery(
            company_id=company.id,
            route_id=route.id,
            address="B",
            lat=36.77,
            lon=3.08,
            status="assigned",
        )
        s.add_all([d1, d2])
        await s.flush()
        s.add_all(
            [
                RouteStop(route_id=route.id, delivery_id=d1.id, sequence=0),
                RouteStop(route_id=route.id, delivery_id=d2.id, sequence=1),
            ]
        )
        await s.commit()
        return {"route": str(route.id), "va": str(va.id), "vb": str(vb.id), "d1": str(d1.id)}


async def _login(client: AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "khaled@acme.dz", "password": "supersecret"}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_reassign_redistributes_to_other_vehicles(ctx) -> None:
    client, sm, redis = ctx
    ids = await _seed(sm)
    headers = await _login(client)

    resp = await client.post(f"/api/v1/routes/{ids['route']}/reassign", headers=headers, json={})
    assert resp.status_code == 202, resp.text
    job_id = resp.json()["job_id"]

    async with sm() as s:
        # Blocked route retired; its stops detached and routable again.
        route = await s.get(Route, uuid.UUID(ids["route"]))
        assert route.status == "cancelled"
        deliveries = list(
            await s.scalars(select(Delivery).where(Delivery.company_id == route.company_id))
        )
        assert all(d.route_id is None and d.status == "geocoded" for d in deliveries)
        job = await s.get(OptimizationJob, uuid.UUID(job_id))
        assert job.trigger == "reassign"
        assert job.vehicle_count == 1  # only vehicle B

    # The enqueued problem targets B (not the blocked A) with both stops.
    queued = await redis.lrange("queue:optimize", 0, -1)
    assert len(queued) == 1
    msg = json.loads(queued[0])
    assert [v["id"] for v in msg["vehicles"]] == [ids["vb"]]
    assert len(msg["deliveries"]) == 2


async def test_reassign_requires_another_vehicle(ctx) -> None:
    client, sm, _ = ctx
    ids = await _seed(sm)
    headers = await _login(client)
    # Soft-delete vehicle B so no other vehicle can take over.
    async with sm() as s:
        vb = await s.get(Vehicle, uuid.UUID(ids["vb"]))
        vb.deleted_at = datetime.now(UTC)
        await s.commit()

    resp = await client.post(f"/api/v1/routes/{ids['route']}/reassign", headers=headers, json={})
    assert resp.status_code == 422, resp.text
