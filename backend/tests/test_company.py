"""Company + white-label branding (F16) against Postgres."""

import os

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
async def client():
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


async def test_get_company_and_update_branding(client) -> None:
    headers = await _admin(client)

    got = await client.get("/api/v1/company", headers=headers)
    assert got.status_code == 200, got.text
    assert got.json()["name"] == "Acme"
    assert got.json()["branding"] is None

    upd = await client.put(
        "/api/v1/company/branding",
        headers=headers,
        json={"brand_name": "Livraison Express", "primary_color": "#EF4444"},
    )
    assert upd.status_code == 200, upd.text
    assert upd.json()["branding"]["brand_name"] == "Livraison Express"
    assert upd.json()["branding"]["primary_color"] == "#EF4444"

    # Partial update merges (keeps brand_name, adds logo).
    upd2 = await client.put(
        "/api/v1/company/branding",
        headers=headers,
        json={"logo_url": "https://cdn.dz/logo.png"},
    )
    branding = upd2.json()["branding"]
    assert branding["brand_name"] == "Livraison Express"
    assert branding["logo_url"] == "https://cdn.dz/logo.png"


async def test_invalid_color_rejected(client) -> None:
    headers = await _admin(client)
    resp = await client.put(
        "/api/v1/company/branding", headers=headers, json={"primary_color": "red"}
    )
    assert resp.status_code == 422


async def test_branding_update_is_admin_only(client) -> None:
    headers = await _admin(client)
    await client.post(
        "/api/v1/fleet/drivers",
        headers=headers,
        json={"email": "drv@acme.dz", "password": "supersecret", "full_name": "Drv"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": "drv@acme.dz", "password": "supersecret"}
    )
    drv = {"Authorization": f"Bearer {login.json()['access_token']}"}
    # A driver can read the company...
    assert (await client.get("/api/v1/company", headers=drv)).status_code == 200
    # ...but not change branding.
    resp = await client.put("/api/v1/company/branding", headers=drv, json={"brand_name": "Nope"})
    assert resp.status_code == 401
