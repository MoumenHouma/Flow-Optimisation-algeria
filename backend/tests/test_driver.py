"""Driver PWA runtime (F8) against Postgres. Skipped without TEST_DATABASE_URL."""

import os
import uuid

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
from routeopt.models.delivery_status_history import DeliveryStatusHistory
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


async def _seed(sessionmaker):
    """A company + driver + vehicle(driver) + route with two stops."""
    async with sessionmaker() as s:
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
        route = Route(
            company_id=company.id, vehicle_id=vehicle.id, total_distance_m=1000, status="planned"
        )
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
            lat=36.76,
            lon=3.07,
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
        return {"d1": str(d1.id), "d2": str(d2.id), "route": str(route.id)}


async def _login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_driver_route_and_status_flow(ctx) -> None:
    client, sessionmaker = ctx
    ids = await _seed(sessionmaker)
    headers = await _login(client, "amine@acme.dz", "supersecret")

    # Driver sees their route with progress 0/2
    route = await client.get("/api/v1/driver/route", headers=headers)
    assert route.status_code == 200, route.text
    body = route.json()
    assert body["vehicle_name"] == "Fourgon 1"
    assert body["delivered"] == 0 and body["total"] == 2
    assert [s["sequence"] for s in body["stops"]] == [0, 1]

    # Mark the first stop delivered
    upd = await client.put(
        f"/api/v1/driver/deliveries/{ids['d1']}/status",
        headers=headers,
        json={"status": "delivered", "lat": 36.75, "lon": 3.06},
    )
    assert upd.status_code == 200, upd.text
    assert upd.json()["status"] == "delivered"

    # Progress now 1/2, route flipped to in_progress
    body2 = (await client.get("/api/v1/driver/route", headers=headers)).json()
    assert body2["delivered"] == 1

    # History row recorded
    async with sessionmaker() as s:
        from sqlalchemy import select

        rows = list(
            await s.scalars(
                select(DeliveryStatusHistory).where(
                    DeliveryStatusHistory.delivery_id == uuid.UUID(ids["d1"])
                )
            )
        )
    assert len(rows) == 1
    assert rows[0].to_status == "delivered"
    assert rows[0].from_status == "assigned"


async def test_cannot_update_foreign_delivery(ctx) -> None:
    client, sessionmaker = ctx
    await _seed(sessionmaker)
    headers = await _login(client, "amine@acme.dz", "supersecret")
    # A random delivery id the driver doesn't own -> 404
    resp = await client.put(
        f"/api/v1/driver/deliveries/{uuid.uuid4()}/status",
        headers=headers,
        json={"status": "delivered"},
    )
    assert resp.status_code == 404


async def test_create_driver_and_duplicate(ctx) -> None:
    client, sessionmaker = ctx
    # Register an admin/manager to create drivers
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Beta",
            "email": "mgr@beta.dz",
            "password": "supersecret",
            "full_name": "Manager",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}

    created = await client.post(
        "/api/v1/fleet/drivers",
        headers=headers,
        json={"email": "karim@beta.dz", "password": "supersecret", "full_name": "Karim"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["role"] == "driver"

    dup = await client.post(
        "/api/v1/fleet/drivers",
        headers=headers,
        json={"email": "karim@beta.dz", "password": "supersecret", "full_name": "Karim2"},
    )
    assert dup.status_code == 409
