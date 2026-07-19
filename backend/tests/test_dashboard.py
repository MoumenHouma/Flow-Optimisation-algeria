"""Dashboard KPI aggregation (F6) against Postgres. Skipped without TEST_DATABASE_URL."""

import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from routeopt.database import get_session
from routeopt.main import app
from routeopt.models import Base
from routeopt.models.route import Route

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


async def _auth(client: AsyncClient) -> tuple[dict[str, str], str]:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Acme",
            "email": "k@acme.dz",
            "password": "supersecret",
            "full_name": "Khaled",
        },
    )
    headers = {"Authorization": f"Bearer {reg.json()['access_token']}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    return headers, me.json()["company_id"]


async def test_dashboard_summary(ctx) -> None:
    client, sessionmaker = ctx
    headers, company_id = await _auth(client)

    await client.post(
        "/api/v1/fleet/vehicles",
        headers=headers,
        json={
            "name": "V1",
            "capacity_weight": 500,
            "depot": {"lat": 36.75, "lon": 3.06},
            "depot_address": "Dépôt",
        },
    )
    await client.post(
        "/api/v1/orders",
        headers=headers,
        json=[
            {"address": "A", "lat": 36.75, "lon": 3.06, "weight": 5},
            {"address": "B", "lat": 36.76, "lon": 3.07, "weight": 8},
        ],
    )

    # Before any route
    s1 = (await client.get("/api/v1/dashboard/summary", headers=headers)).json()
    assert s1["deliveries_total"] == 2
    assert s1["deliveries_by_status"]["geocoded"] == 2
    assert s1["vehicles_active"] == 1 and s1["vehicles_total"] == 1
    assert s1["today_routes"] == 0
    assert s1["today_distance_m"] == 0

    # Seed a route created "today" directly
    async with sessionmaker() as session:
        session.add(
            Route(
                company_id=uuid.UUID(company_id),
                total_distance_m=1500,
                total_time_s=600,
                status="planned",
            )
        )
        await session.commit()

    s2 = (await client.get("/api/v1/dashboard/summary", headers=headers)).json()
    assert s2["today_routes"] == 1
    assert s2["today_distance_m"] == 1500
    assert s2["today_time_s"] == 600
    assert s2["week_distance_m"] == 1500
