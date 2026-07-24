"""Live tracking + notifications (F18) against Postgres + fakeredis.

Covers driver location → Redis (tenant-scoped, surfaced on the public link),
signed-token validation, and that a status change enqueues a customer message
without sending it. The infinite SSE stream is intentionally not exercised here.
"""

import json
import os

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from routeopt.core.security import hash_password
from routeopt.database import get_session
from routeopt.main import app
from routeopt.models import Base
from routeopt.models.company import Company
from routeopt.models.delivery import Delivery
from routeopt.models.route import Route, RouteStop
from routeopt.models.user import User
from routeopt.models.vehicle import Vehicle
from routeopt.modules.tracking.tokens import make_token

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB_URL, reason="TEST_DATABASE_URL not set")


@pytest_asyncio.fixture
async def fake_redis(monkeypatch):
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    for mod in (
        "routeopt.core.dependencies",
        "routeopt.modules.driver.service",
        "routeopt.modules.tracking.router",
    ):
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
    async with sm() as s:
        company = Company(name="Acme")
        s.add(company)
        await s.flush()
        driver = User(
            company_id=company.id,
            email="amine@acme.dz",
            password_hash=hash_password("supersecret"),
            full_name="Amine",
            role="driver",
        )
        s.add(driver)
        await s.flush()
        vehicle = Vehicle(
            company_id=company.id,
            driver_user_id=driver.id,
            name="Fourgon 1",
            depot_lat=36.7538,
            depot_lon=3.0588,
            depot_address="Dépôt",
        )
        s.add(vehicle)
        await s.flush()
        route = Route(company_id=company.id, vehicle_id=vehicle.id, status="dispatched")
        s.add(route)
        await s.flush()
        d1 = Delivery(
            company_id=company.id,
            route_id=route.id,
            address="A",
            lat=36.75,
            lon=3.06,
            status="assigned",
            customer_phone="+213555000111",
        )
        s.add(d1)
        await s.flush()
        s.add(RouteStop(route_id=route.id, delivery_id=d1.id, sequence=0))
        await s.commit()
        return {"delivery": str(d1.id), "vehicle": str(vehicle.id)}


async def _login(client: AsyncClient, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_location_surfaces_on_public_track(ctx) -> None:
    client, sm, _ = ctx
    ids = await _seed(sm)
    driver = await _login(client, "amine@acme.dz")

    loc = await client.post(
        "/api/v1/driver/location", headers=driver, json={"lat": 36.74, "lon": 3.05}
    )
    assert loc.status_code == 204, loc.text

    # Public tracking link (no auth) shows status + the live vehicle dot.
    token = make_token(ids["delivery"])
    tracked = await client.get(f"/api/v1/track/{token}")
    assert tracked.status_code == 200, tracked.text
    body = tracked.json()
    assert body["status"] == "assigned"
    assert body["vehicle_position"]["vehicle_id"] == ids["vehicle"]
    assert body["vehicle_position"]["lat"] == 36.74

    # A tampered token is rejected.
    assert (await client.get("/api/v1/track/not-a-real-token")).status_code == 404


async def test_status_change_enqueues_notification(ctx) -> None:
    client, sm, redis = ctx
    ids = await _seed(sm)
    driver = await _login(client, "amine@acme.dz")

    upd = await client.put(
        f"/api/v1/driver/deliveries/{ids['delivery']}/status",
        headers=driver,
        json={"status": "en_route"},
    )
    assert upd.status_code == 200, upd.text

    # The customer message was queued (not sent) with a tracking link.
    queued = await redis.lrange("queue:notifications", 0, -1)
    assert len(queued) == 1
    msg = json.loads(queued[0])
    assert msg["to"] == "+213555000111"
    assert "/track/" in msg["body"]
