"""Territory management (F15).

The clustering test is pure (no DB). The API tests run against Postgres and cover
auto-generation (zones + driver assignment + delivery membership), CRUD and scope.
Skipped without TEST_DATABASE_URL where noted.
"""

import os

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
from routeopt.models.user import User
from routeopt.modules.territories.clustering import kmeans

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")


def test_kmeans_partitions_two_clusters() -> None:
    # Two tight groups far apart → two clusters, correct membership.
    points = [(36.75, 3.05), (36.76, 3.06), (35.69, -0.63), (35.70, -0.64)]
    assignment, centroids = kmeans(points, 2)
    assert len(centroids) == 2
    # The first two points share a cluster; the last two share the other.
    assert assignment[0] == assignment[1]
    assert assignment[2] == assignment[3]
    assert assignment[0] != assignment[2]


def test_kmeans_clamps_k_to_point_count() -> None:
    assignment, centroids = kmeans([(36.75, 3.05)], 5)
    assert len(centroids) == 1
    assert assignment == [0]


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


async def _seed(client, sessionmaker) -> dict[str, str]:
    headers = await _admin(client)
    async with sessionmaker() as s:
        company_id = (await s.scalars(select(User.company_id))).first()
        # Two drivers so zones can be assigned round-robin.
        for i in range(2):
            s.add(
                User(
                    company_id=company_id,
                    email=f"drv{i}@acme.dz",
                    password_hash=hash_password("x"),
                    full_name=f"Driver {i}",
                    role="driver",
                )
            )
        # Two tight delivery clusters far apart.
        for lat, lon in [(36.75, 3.05), (36.76, 3.06), (35.69, -0.63), (35.70, -0.64)]:
            s.add(Delivery(company_id=company_id, address="A", lat=lat, lon=lon, status="geocoded"))
        await s.commit()
    return headers


async def test_auto_generate_zones_and_assign(ctx) -> None:
    client, sessionmaker = ctx
    headers = await _seed(client, sessionmaker)

    resp = await client.post(
        "/api/v1/territories/auto-generate", headers=headers, json={"zones": 2}
    )
    assert resp.status_code == 201, resp.text
    zones = resp.json()
    assert len(zones) == 2
    # Every delivery landed in a zone.
    assert sum(z["delivery_count"] for z in zones) == 4
    # Drivers assigned round-robin (both distinct).
    driver_ids = {z["driver_user_id"] for z in zones}
    assert None not in driver_ids and len(driver_ids) == 2
    assert all(z["centroid"] is not None for z in zones)

    listed = await client.get("/api/v1/territories", headers=headers)
    assert len(listed.json()) == 2


async def test_territory_crud_and_scope(ctx) -> None:
    client, _ = ctx
    headers = await _admin(client)

    created = await client.post(
        "/api/v1/territories", headers=headers, json={"name": "Centre", "color": "#10B981"}
    )
    assert created.status_code == 201, created.text
    tid = created.json()["id"]

    updated = await client.put(
        f"/api/v1/territories/{tid}", headers=headers, json={"name": "Alger Centre"}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Alger Centre"

    removed = await client.delete(f"/api/v1/territories/{tid}", headers=headers)
    assert removed.status_code == 204
    assert (await client.get("/api/v1/territories", headers=headers)).json() == []


async def test_auto_generate_requires_deliveries(ctx) -> None:
    client, _ = ctx
    headers = await _admin(client)
    resp = await client.post("/api/v1/territories/auto-generate", headers=headers, json={})
    assert resp.status_code == 422
