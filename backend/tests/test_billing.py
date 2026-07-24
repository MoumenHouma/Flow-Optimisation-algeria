"""Billing + quota enforcement (F19) against Postgres. Skipped without TEST_DATABASE_URL.

Covers the delivery-per-day quota, an admin plan change lifting caps immediately,
recording an offline payment into a paid invoice, and admin-only gating.
"""

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
        yield client, sessionmaker
    app.dependency_overrides.clear()
    await engine.dispose()


async def _seed(sessionmaker):
    """A free-plan company (2 deliveries/day cap) with an admin and a manager."""
    async with sessionmaker() as s:
        company = Company(name="Acme", plan="free", max_vehicles=1, max_deliveries_per_day=2)
        s.add(company)
        await s.flush()
        s.add_all(
            [
                User(
                    company_id=company.id,
                    email="admin@acme.dz",
                    password_hash=hash_password("supersecret"),
                    full_name="Sofiane",
                    role="admin",
                ),
                User(
                    company_id=company.id,
                    email="khaled@acme.dz",
                    password_hash=hash_password("supersecret"),
                    full_name="Khaled",
                    role="manager",
                ),
            ]
        )
        await s.commit()


async def _login(client: AsyncClient, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "supersecret"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _deliveries(n: int):
    return [{"address": f"Rue {i}", "lat": 36.75, "lon": 3.06} for i in range(n)]


async def test_delivery_quota_then_upgrade_lifts_it(ctx) -> None:
    client, sessionmaker = ctx
    await _seed(sessionmaker)
    admin = await _login(client, "admin@acme.dz")
    manager = await _login(client, "khaled@acme.dz")

    # Free plan cap is 2/day — a 3-row import is rejected.
    over = await client.post("/api/v1/orders", headers=manager, json=_deliveries(3))
    assert over.status_code == 409, over.text
    assert "quota" in over.text.lower()

    # Admin upgrades to pro (cap 500) — caps come from the DB, no re-login needed.
    up = await client.put("/api/v1/billing/plan", headers=admin, json={"plan": "pro"})
    assert up.status_code == 200, up.text
    assert up.json()["plan"] == "pro"
    assert up.json()["usage"]["max_deliveries_per_day"] == 500

    # The same import now succeeds on the lifted cap.
    ok = await client.post("/api/v1/orders", headers=manager, json=_deliveries(3))
    assert ok.status_code == 201, ok.text
    assert ok.json()["created"] == 3


async def test_billing_usage_and_payment(ctx) -> None:
    client, sessionmaker = ctx
    await _seed(sessionmaker)
    admin = await _login(client, "admin@acme.dz")

    billing = (await client.get("/api/v1/billing", headers=admin)).json()
    assert billing["plan"] == "free"
    assert billing["usage"]["max_deliveries_per_day"] == 2

    await client.put("/api/v1/billing/plan", headers=admin, json={"plan": "starter"})
    pay = await client.post(
        "/api/v1/billing/invoices/pay",
        headers=admin,
        json={"period": "2026-07", "method": "baridimob", "reference": "TX-42"},
    )
    assert pay.status_code == 201, pay.text
    body = pay.json()
    assert body["status"] == "paid"
    assert body["amount_da"] == 2500
    assert body["method"] == "baridimob"

    invoices = (await client.get("/api/v1/billing/invoices", headers=admin)).json()
    assert len(invoices) == 1 and invoices[0]["period"] == "2026-07"


async def test_change_plan_is_admin_only(ctx) -> None:
    client, sessionmaker = ctx
    await _seed(sessionmaker)
    manager = await _login(client, "khaled@acme.dz")
    resp = await client.put("/api/v1/billing/plan", headers=manager, json={"plan": "pro"})
    assert resp.status_code == 403
