"""Analytics (F11) against Postgres — trends + performance from status history.

Seeds delivery_status_history + routes directly, then reads the aggregates back
through the API as a manager. Skipped unless TEST_DATABASE_URL is set.
"""

import os
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from routeopt.core.security import hash_password
from routeopt.database import get_session
from routeopt.main import app
from routeopt.models import Base
from routeopt.models.delivery import Delivery
from routeopt.models.delivery_status_history import DeliveryStatusHistory
from routeopt.models.route import Route
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


async def _register(client: AsyncClient) -> dict[str, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Acme",
            "email": "mgr@acme.dz",
            "password": "supersecret",
            "full_name": "Manager",
        },
    )
    assert reg.status_code == 201, reg.text
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}


async def _seed(sessionmaker) -> None:
    """2 delivered + 1 failed (by a driver) + 1 route (2 km), all today."""
    async with sessionmaker() as s:
        company_id = (await s.scalars(select(User.company_id))).first()
        driver = User(
            company_id=company_id,
            email="amine@acme.dz",
            password_hash=hash_password("supersecret"),
            full_name="Amine",
            role="driver",
        )
        s.add(driver)
        await s.flush()

        now = datetime.now(UTC)
        for i, (status, reason) in enumerate(
            [("delivered", None), ("delivered", None), ("failed", "client_absent")]
        ):
            d = Delivery(company_id=company_id, address=f"A{i}", lat=36.75, lon=3.06, status=status)
            s.add(d)
            await s.flush()
            s.add(
                DeliveryStatusHistory(
                    delivery_id=d.id,
                    from_status="assigned",
                    to_status=status,
                    reason=reason,
                    changed_by_user_id=driver.id,
                    created_at=now,
                )
            )
        s.add(
            Route(
                company_id=company_id, total_distance_m=2000, total_time_s=600, status="completed"
            )
        )
        await s.commit()


async def test_performance_aggregates(ctx) -> None:
    client, sessionmaker = ctx
    headers = await _register(client)
    await _seed(sessionmaker)

    resp = await client.get("/api/v1/analytics/performance?days=30", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["delivered"] == 2
    assert body["failed"] == 1
    assert body["success_rate"] == pytest.approx(0.6667, abs=1e-4)
    assert body["routes"] == 1
    assert body["total_distance_m"] == 2000
    assert body["avg_distance_per_route_m"] == 2000
    assert body["failure_reasons"] == [{"reason": "client_absent", "count": 1}]
    assert len(body["drivers"]) == 1
    assert body["drivers"][0]["driver_name"] == "Amine"
    assert body["drivers"][0]["delivered"] == 2
    assert body["drivers"][0]["failed"] == 1


async def test_trends_buckets(ctx) -> None:
    client, sessionmaker = ctx
    headers = await _register(client)
    await _seed(sessionmaker)

    resp = await client.get("/api/v1/analytics/trends?days=7", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["days"] == 7
    assert len(body["points"]) == 7
    today = datetime.now(UTC).date().isoformat()
    point = next(p for p in body["points"] if p["date"] == today)
    assert point["deliveries_completed"] == 2
    assert point["deliveries_failed"] == 1
    assert point["routes"] == 1
    assert point["distance_m"] == 2000
    # Days with no activity are still present as zero-filled buckets.
    assert all(p["deliveries_completed"] == 0 for p in body["points"] if p["date"] != today)


async def test_analytics_rejects_non_manager(ctx) -> None:
    client, sessionmaker = ctx
    await _register(client)
    await _seed(sessionmaker)
    # A driver (non-manager) is forbidden (insufficient role → 403).
    login = await client.post(
        "/api/v1/auth/login", json={"email": "amine@acme.dz", "password": "supersecret"}
    )
    driver_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    resp = await client.get("/api/v1/analytics/performance", headers=driver_headers)
    assert resp.status_code == 403


async def test_empty_company_is_zeroed(ctx) -> None:
    client, _ = ctx
    headers = await _register(client)
    perf = await client.get("/api/v1/analytics/performance", headers=headers)
    assert perf.status_code == 200
    assert perf.json()["success_rate"] == 0.0
    assert perf.json()["delivered"] == 0
