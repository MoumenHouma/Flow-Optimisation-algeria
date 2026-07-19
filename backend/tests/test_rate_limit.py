"""Per-plan rate limiting (PRD §5.1). Free plan = 10 req/min."""

import os

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from routeopt.core.dependencies import _PLAN_LIMITS
from routeopt.database import get_session
from routeopt.main import app
from routeopt.models import Base

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB_URL, reason="TEST_DATABASE_URL not set")


def test_plan_limit_map() -> None:
    assert _PLAN_LIMITS == {"free": 10, "starter": 100, "pro": 1000, "enterprise": None}


@pytest_asyncio.fixture
async def client(monkeypatch):
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("routeopt.core.dependencies.redis_client", fake)
    monkeypatch.setattr("routeopt.modules.routes.service.redis_client", fake)

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


async def test_free_plan_rate_limited_after_10(client: AsyncClient) -> None:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Acme",
            "email": "k@acme.dz",
            "password": "supersecret",
            "full_name": "Khaled",
        },
    )
    assert reg.status_code == 201
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    # rate_limiter runs before the body; empty optimize bodies 422, but still count.
    statuses = []
    for _ in range(11):
        resp = await client.post("/api/v1/routes/optimize", headers=headers, json={})
        statuses.append(resp.status_code)

    assert 429 not in statuses[:10]  # first 10 within the free limit
    assert statuses[10] == 429  # 11th exceeds free plan (10/min)
