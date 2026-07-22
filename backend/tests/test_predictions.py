"""Service-time prediction (F13) against Postgres.

Seeds delivery_status_history with known en_route→delivered deltas, trains the
cohort model, and checks the summary, the learned median, prediction via the
optimize payload, and access control. Skipped without TEST_DATABASE_URL.
"""

import json
import os
from datetime import UTC, datetime, time, timedelta

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from routeopt.database import get_session
from routeopt.main import app
from routeopt.models import Base
from routeopt.models.delivery import Delivery
from routeopt.models.delivery_status_history import DeliveryStatusHistory
from routeopt.models.user import User

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
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, sessionmaker, fake_redis
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


async def _seed_history(sessionmaker, durations_s: list[int]) -> None:
    """Deliveries in one cohort, each with an en_route→delivered pair of a given duration."""
    async with sessionmaker() as s:
        company_id = (await s.scalars(select(User.company_id))).first()
        base = datetime(2026, 7, 1, 9, 0, tzinfo=UTC)
        for i, dur in enumerate(durations_s):
            d = Delivery(
                company_id=company_id,
                address=f"A{i}",
                lat=36.75,
                lon=3.06,
                status="delivered",
                priority=1,
                weight=3,
                time_window_start=time(9, 0),
                time_window_end=time(12, 0),
            )
            s.add(d)
            await s.flush()
            s.add(DeliveryStatusHistory(delivery_id=d.id, to_status="en_route", created_at=base))
            s.add(
                DeliveryStatusHistory(
                    delivery_id=d.id,
                    from_status="en_route",
                    to_status="delivered",
                    created_at=base + timedelta(seconds=dur),
                )
            )
        await s.commit()


async def test_train_learns_cohort_median(ctx) -> None:
    client, sessionmaker, _ = ctx
    headers = await _admin(client)
    # Five deliveries in one cohort; median duration = 600s.
    await _seed_history(sessionmaker, [400, 500, 600, 700, 800])

    trained = await client.post("/api/v1/predictions/service-time/train", headers=headers)
    assert trained.status_code == 200, trained.text
    body = trained.json()
    assert body["trained"] is True
    assert body["sample_count"] == 5
    assert body["cohort_count"] == 1
    assert body["global_median_s"] == 600

    # Summary reflects the trained model.
    summary = await client.get("/api/v1/predictions/service-time", headers=headers)
    assert summary.json()["cohort_count"] == 1


async def test_prediction_feeds_optimize_payload(ctx) -> None:
    client, sessionmaker, fake_redis = ctx
    headers = await _admin(client)
    await _seed_history(sessionmaker, [600, 600, 600, 600])
    await client.post("/api/v1/predictions/service-time/train", headers=headers)

    # A vehicle + a fresh routable delivery in the same cohort.
    await client.post(
        "/api/v1/fleet/vehicles",
        headers=headers,
        json={
            "name": "Camion 1",
            "capacity_weight": 500,
            "depot": {"lat": 36.75, "lon": 3.05},
            "depot_address": "Dépôt",
        },
    )
    await client.post(
        "/api/v1/orders",
        headers=headers,
        json=[
            {
                "address": "New",
                "lat": 36.75,
                "lon": 3.06,
                "weight": 3,
                "priority": 1,
                "time_window_start": "09:00",
                "time_window_end": "12:00",
            }
        ],
    )

    submit = await client.post("/api/v1/routes/optimize", headers=headers, json={})
    assert submit.status_code == 202, submit.text
    msg = json.loads((await fake_redis.lrange("queue:optimize", 0, -1))[-1])
    # Service time comes from the trained cohort model (600s), not the 300s default.
    assert msg["deliveries"][0]["service_time"] == 600


async def test_summary_untrained_and_auth(ctx) -> None:
    client, sessionmaker, _ = ctx
    headers = await _admin(client)

    # Untrained placeholder.
    summary = await client.get("/api/v1/predictions/service-time", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["trained"] is False
    assert summary.json()["global_median_s"] == 300

    # A driver may not train.
    await client.post(
        "/api/v1/fleet/drivers",
        headers=headers,
        json={"email": "drv@acme.dz", "password": "supersecret", "full_name": "Drv"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": "drv@acme.dz", "password": "supersecret"}
    )
    drv = {"Authorization": f"Bearer {login.json()['access_token']}"}
    denied = await client.post("/api/v1/predictions/service-time/train", headers=drv)
    assert denied.status_code == 401
