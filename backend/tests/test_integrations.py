"""Public API + webhooks (F10) against Postgres.

Covers API-key lifecycle, key-authed public endpoints with scope enforcement,
and signed webhook dispatch on a driver status change. Object storage / geocoding
aren't needed (deliveries are created with coordinates). Skipped without
TEST_DATABASE_URL.
"""

import json
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from routeopt.core.security import hash_password
from routeopt.core.webhooks import sign
from routeopt.database import get_session
from routeopt.main import app
from routeopt.models import Base
from routeopt.models.delivery import Delivery
from routeopt.models.route import Route, RouteStop
from routeopt.models.user import User
from routeopt.models.vehicle import Vehicle

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


async def _admin(client: AsyncClient) -> tuple[dict[str, str], str]:
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
    return {"Authorization": f"Bearer {reg.json()['access_token']}"}, reg.json()["access_token"]


async def _make_key(client: AsyncClient, headers, scope: str) -> str:
    resp = await client.post(
        "/api/v1/integrations/api-keys",
        headers=headers,
        json={"name": f"{scope} key", "scope": scope},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["key"]


async def test_api_key_lifecycle_and_public_api(ctx) -> None:
    client, _ = ctx
    headers, _ = await _admin(client)

    create = await client.post(
        "/api/v1/integrations/api-keys",
        headers=headers,
        json={"name": "Shopify", "scope": "write"},
    )
    assert create.status_code == 201, create.text
    body = create.json()
    key = body["key"]
    assert key.startswith("rk_live_")
    assert body["key_prefix"] == key[:12]

    listed = await client.get("/api/v1/integrations/api-keys", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["scope"] == "write"

    # Create a delivery through the public API using the key.
    created = await client.post(
        "/api/public/v1/deliveries",
        headers={"X-API-Key": key},
        json={"order_id": "SHOP-1", "address": "12 Rue Didouche", "lat": 36.75, "lon": 3.06},
    )
    assert created.status_code == 201, created.text
    did = created.json()["id"]
    assert created.json()["status"] == "geocoded"

    # Track it back.
    got = await client.get(f"/api/public/v1/deliveries/{did}", headers={"X-API-Key": key})
    assert got.status_code == 200
    assert got.json()["order_id"] == "SHOP-1"

    # A bad key is rejected.
    bad = await client.get("/api/public/v1/deliveries", headers={"X-API-Key": "rk_live_nope"})
    assert bad.status_code == 401

    # Revoke, then the key stops working.
    key_id = listed.json()[0]["id"]
    rev = await client.delete(f"/api/v1/integrations/api-keys/{key_id}", headers=headers)
    assert rev.status_code == 204
    after = await client.get("/api/public/v1/deliveries", headers={"X-API-Key": key})
    assert after.status_code == 401


async def test_read_scope_cannot_write(ctx) -> None:
    client, _ = ctx
    headers, _ = await _admin(client)
    key = await _make_key(client, headers, "read")

    # read scope can list...
    ok = await client.get("/api/public/v1/deliveries", headers={"X-API-Key": key})
    assert ok.status_code == 200
    # ...but cannot create.
    denied = await client.post(
        "/api/public/v1/deliveries",
        headers={"X-API-Key": key},
        json={"address": "A", "lat": 36.75, "lon": 3.06},
    )
    assert denied.status_code == 401


async def test_only_admin_manages_keys(ctx) -> None:
    client, sessionmaker = ctx
    headers, _ = await _admin(client)
    # Onboard a driver and log in as them.
    await client.post(
        "/api/v1/fleet/drivers",
        headers=headers,
        json={"email": "drv@acme.dz", "password": "supersecret", "full_name": "Drv"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": "drv@acme.dz", "password": "supersecret"}
    )
    drv_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    resp = await client.get("/api/v1/integrations/api-keys", headers=drv_headers)
    assert resp.status_code == 401


async def _seed_driver_route(sessionmaker) -> tuple[str, str]:
    async with sessionmaker() as s:
        from sqlalchemy import select

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
        vehicle = Vehicle(
            company_id=company_id,
            driver_user_id=driver.id,
            name="Fourgon 1",
            depot_lat=36.75,
            depot_lon=3.05,
            depot_address="Dépôt",
        )
        s.add(vehicle)
        await s.flush()
        route = Route(company_id=company_id, vehicle_id=vehicle.id, status="planned")
        s.add(route)
        await s.flush()
        d = Delivery(
            company_id=company_id,
            route_id=route.id,
            address="A",
            lat=36.75,
            lon=3.06,
            status="assigned",
        )
        s.add(d)
        await s.flush()
        s.add(RouteStop(route_id=route.id, delivery_id=d.id, sequence=0))
        await s.commit()
        return str(d.id), str(company_id)


async def test_webhook_dispatched_on_status_change(ctx, monkeypatch) -> None:
    client, sessionmaker = ctx
    headers, _ = await _admin(client)

    reg = await client.post(
        "/api/v1/integrations/webhooks",
        headers=headers,
        json={"url": "https://example.test/hook", "events": ["delivery.status_changed"]},
    )
    assert reg.status_code == 201, reg.text
    secret = reg.json()["secret"]
    assert len(secret) == 64

    calls: list[dict] = []

    async def fake_post(url: str, event: str, body: str, sec: str) -> None:
        calls.append({"url": url, "event": event, "body": body, "secret": sec})

    monkeypatch.setattr("routeopt.core.webhooks._post", fake_post)

    delivery_id, _ = await _seed_driver_route(sessionmaker)
    login = await client.post(
        "/api/v1/auth/login", json={"email": "amine@acme.dz", "password": "supersecret"}
    )
    drv_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    upd = await client.put(
        f"/api/v1/driver/deliveries/{delivery_id}/status",
        headers=drv_headers,
        json={"status": "delivered"},
    )
    assert upd.status_code == 200, upd.text

    # Exactly one signed webhook was delivered.
    assert len(calls) == 1
    call = calls[0]
    assert call["url"] == "https://example.test/hook"
    assert call["event"] == "delivery.status_changed"
    assert call["secret"] == secret
    payload = json.loads(call["body"])
    assert payload["event"] == "delivery.status_changed"
    assert payload["data"]["delivery_id"] == delivery_id
    assert payload["data"]["status"] == "delivered"
    # Signature the receiver would verify.
    assert sign(secret, call["body"])


async def test_unknown_webhook_event_rejected(ctx) -> None:
    client, _ = ctx
    headers, _ = await _admin(client)
    resp = await client.post(
        "/api/v1/integrations/webhooks",
        headers=headers,
        json={"url": "https://example.test/hook", "events": ["nope.bad"]},
    )
    assert resp.status_code == 422
