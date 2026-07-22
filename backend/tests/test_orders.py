"""Orders (F1) against Postgres + fakeredis.

Covers bulk create, routable listing, RBAC (viewer cannot create) and tenant
isolation (one company never sees another's deliveries). Skipped without
TEST_DATABASE_URL.
"""

import os

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
    sm = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session():
        async with sm() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac, sm
    app.dependency_overrides.clear()
    await engine.dispose()


async def _register(client: AsyncClient, email: str, company: str) -> dict[str, str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": company,
            "email": email,
            "password": "supersecret",
            "full_name": "Boss",
        },
    )
    assert reg.status_code == 201, reg.text
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}


async def test_bulk_create_and_list_routable(ctx) -> None:
    client, _ = ctx
    headers = await _register(client, "boss@acme.dz", "Acme")

    # Coordinate-bearing rows skip geocoding (no live Nominatim call in tests).
    resp = await client.post(
        "/api/v1/orders",
        headers=headers,
        json=[
            {"address": "12 Rue Didouche", "lat": 36.75, "lon": 3.06, "weight": 5},
            {"address": "45 Bd Mohamed V", "lat": 36.76, "lon": 3.07, "weight": 3},
        ],
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["created"] == 2
    assert body["geocoding_pending"] == 0  # both had coordinates

    # Both geocoded deliveries are routable.
    routable = await client.get("/api/v1/orders", headers=headers)
    assert routable.status_code == 200
    addresses = {d["address"] for d in routable.json()}
    assert addresses == {"12 Rue Didouche", "45 Bd Mohamed V"}


async def test_create_requires_manager_role(ctx) -> None:
    client, sm = ctx
    await _register(client, "boss@acme.dz", "Acme")  # creates the company

    # Seed a viewer and log in as them.
    async with sm() as s:
        company_id = (await s.scalars(select(User.company_id))).first()
        s.add(
            User(
                company_id=company_id,
                email="viewer@acme.dz",
                password_hash=hash_password("supersecret"),
                full_name="Viewer",
                role="viewer",
            )
        )
        await s.commit()
    login = await client.post(
        "/api/v1/auth/login", json={"email": "viewer@acme.dz", "password": "supersecret"}
    )
    viewer = {"Authorization": f"Bearer {login.json()['access_token']}"}

    denied = await client.post(
        "/api/v1/orders",
        headers=viewer,
        json=[{"address": "X", "lat": 36.7, "lon": 3.0}],
    )
    assert denied.status_code == 403


async def test_deliveries_are_tenant_scoped(ctx) -> None:
    client, _ = ctx
    a = await _register(client, "a@acme.dz", "Acme")
    b = await _register(client, "b@beta.dz", "Beta")

    await client.post(
        "/api/v1/orders",
        headers=a,
        json=[{"address": "Chez A", "lat": 36.75, "lon": 3.06}],
    )
    # Company B sees none of company A's deliveries.
    listed_b = await client.get("/api/v1/orders", headers=b)
    assert listed_b.status_code == 200
    assert listed_b.json() == []
