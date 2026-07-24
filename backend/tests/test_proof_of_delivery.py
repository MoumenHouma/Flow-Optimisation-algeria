"""Proof-of-delivery upload/read (F8, SCHEMA §5.3) against Postgres.

Object storage can't run in the sandbox, so a fake ``Storage`` is injected via
the ``get_storage`` dependency — it records puts and mints deterministic URLs.
"""

import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from routeopt.core.security import hash_password
from routeopt.core.storage import get_storage
from routeopt.database import get_session
from routeopt.main import app
from routeopt.models import Base
from routeopt.models.company import Company
from routeopt.models.delivery import Delivery
from routeopt.models.proof_of_delivery import ProofOfDelivery
from routeopt.models.route import Route, RouteStop
from routeopt.models.user import User
from routeopt.models.vehicle import Vehicle

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB_URL, reason="TEST_DATABASE_URL not set")


class FakeStorage:
    """Records uploaded objects; presigns to a deterministic fake URL."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    async def presigned_get(self, key: str, expires_in: int = 3600) -> str:
        return f"https://minio.local/{key}?sig=fake"


@pytest_asyncio.fixture
async def ctx():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    storage = FakeStorage()

    async def override_get_session():
        async with sessionmaker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_storage] = lambda: storage
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, sessionmaker, storage
    app.dependency_overrides.clear()
    await engine.dispose()


async def _seed(sessionmaker):
    """A company + driver + vehicle(driver) + route with one assigned stop."""
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
        s.add(d1)
        await s.flush()
        s.add(RouteStop(route_id=route.id, delivery_id=d1.id, sequence=0))
        await s.commit()
        return {"d1": str(d1.id)}


async def _login(client: AsyncClient, email: str, password: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_upload_and_fetch_proof(ctx) -> None:
    client, sessionmaker, storage = ctx
    ids = await _seed(sessionmaker)
    headers = await _login(client, "amine@acme.dz", "supersecret")

    resp = await client.post(
        f"/api/v1/driver/deliveries/{ids['d1']}/proof",
        headers=headers,
        files={"photo": ("proof.jpg", b"\xff\xd8\xff-jpeg-bytes", "image/jpeg")},
        data={"lat": "36.75", "lon": "3.06"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["photo_url"].startswith("https://minio.local/pod/")
    assert body["signature_url"] is None
    assert body["lat"] == 36.75

    # Object actually stored, and exactly one proof row exists.
    assert len(storage.objects) == 1
    async with sessionmaker() as s:
        rows = list(
            await s.scalars(
                select(ProofOfDelivery).where(ProofOfDelivery.delivery_id == uuid.UUID(ids["d1"]))
            )
        )
    assert len(rows) == 1

    # GET returns the same proof with a presigned URL.
    got = await client.get(f"/api/v1/driver/deliveries/{ids['d1']}/proof", headers=headers)
    assert got.status_code == 200
    assert got.json()["photo_url"].startswith("https://minio.local/pod/")


async def test_reupload_overwrites_single_proof(ctx) -> None:
    client, sessionmaker, storage = ctx
    ids = await _seed(sessionmaker)
    headers = await _login(client, "amine@acme.dz", "supersecret")

    for _ in range(2):
        resp = await client.post(
            f"/api/v1/driver/deliveries/{ids['d1']}/proof",
            headers=headers,
            files={"photo": ("p.jpg", b"bytes", "image/jpeg")},
        )
        assert resp.status_code == 201, resp.text

    async with sessionmaker() as s:
        rows = list(await s.scalars(select(ProofOfDelivery)))
    assert len(rows) == 1  # uq_pod_delivery: still a single proof


async def test_proof_requires_a_file(ctx) -> None:
    client, sessionmaker, _ = ctx
    ids = await _seed(sessionmaker)
    headers = await _login(client, "amine@acme.dz", "supersecret")
    resp = await client.post(f"/api/v1/driver/deliveries/{ids['d1']}/proof", headers=headers)
    assert resp.status_code == 422


async def test_cannot_upload_to_foreign_delivery(ctx) -> None:
    client, sessionmaker, _ = ctx
    await _seed(sessionmaker)
    headers = await _login(client, "amine@acme.dz", "supersecret")
    resp = await client.post(
        f"/api/v1/driver/deliveries/{uuid.uuid4()}/proof",
        headers=headers,
        files={"photo": ("p.jpg", b"bytes", "image/jpeg")},
    )
    assert resp.status_code == 404
