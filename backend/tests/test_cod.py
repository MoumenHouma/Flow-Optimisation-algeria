"""COD reconciliation (F17) against Postgres. Skipped without TEST_DATABASE_URL.

Covers the field-to-manager flow: driver reports cash on a delivered stop, the
record lands in cod_payments, a short amount is flagged as a discrepancy, and the
manager summary/list/reconcile endpoints reflect it.
"""

import os

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
    """A company with a manager, a driver+vehicle, and two COD deliveries."""
    async with sessionmaker() as s:
        company = Company(name="Acme")
        s.add(company)
        await s.flush()
        manager = User(
            company_id=company.id,
            email="khaled@acme.dz",
            password_hash=hash_password("supersecret"),
            full_name="Khaled",
            role="manager",
        )
        driver = User(
            company_id=company.id,
            email="amine@acme.dz",
            password_hash=hash_password("supersecret"),
            full_name="Amine",
            role="driver",
        )
        s.add_all([manager, driver])
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
            cod_amount=1500,
        )
        d2 = Delivery(
            company_id=company.id,
            route_id=route.id,
            address="B",
            lat=36.76,
            lon=3.07,
            status="assigned",
            cod_amount=2000,
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


async def test_cod_collection_and_reconciliation(ctx) -> None:
    client, sessionmaker = ctx
    ids = await _seed(sessionmaker)
    driver_h = await _login(client, "amine@acme.dz", "supersecret")
    manager_h = await _login(client, "khaled@acme.dz", "supersecret")

    # Driver delivers d1 with the exact expected amount -> collected.
    r1 = await client.put(
        f"/api/v1/driver/deliveries/{ids['d1']}/status",
        headers=driver_h,
        json={"status": "delivered", "cod_collected": 1500, "cod_method": "cash"},
    )
    assert r1.status_code == 200, r1.text

    # Driver delivers d2 short -> discrepancy.
    r2 = await client.put(
        f"/api/v1/driver/deliveries/{ids['d2']}/status",
        headers=driver_h,
        json={"status": "delivered", "cod_collected": 1800, "cod_method": "cash"},
    )
    assert r2.status_code == 200, r2.text

    # Manager lists both records.
    payments = await client.get("/api/v1/cod/payments", headers=manager_h)
    assert payments.status_code == 200, payments.text
    rows = payments.json()
    assert len(rows) == 2
    by_status = {row["status"] for row in rows}
    assert by_status == {"collected", "discrepancy"}

    # Summary aggregates expected vs collected with one discrepancy.
    summary = (await client.get("/api/v1/cod/summary", headers=manager_h)).json()
    assert summary["total_expected"] == 3500
    assert summary["total_collected"] == 3300
    assert summary["discrepancies"] == 1

    # Manager reconciles the clean record.
    clean = next(r for r in rows if r["status"] == "collected")
    rec = await client.put(
        f"/api/v1/cod/payments/{clean['id']}",
        headers=manager_h,
        json={"status": "reconciled"},
    )
    assert rec.status_code == 200, rec.text
    assert rec.json()["status"] == "reconciled"


async def test_cod_requires_manager(ctx) -> None:
    client, sessionmaker = ctx
    await _seed(sessionmaker)
    driver_h = await _login(client, "amine@acme.dz", "supersecret")
    # A driver may not read the manager reconciliation view.
    resp = await client.get("/api/v1/cod/payments", headers=driver_h)
    assert resp.status_code == 401
