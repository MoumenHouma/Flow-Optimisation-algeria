"""Geocoder tests (F2). Nominatim HTTP is mocked; cache uses fakeredis."""

import hashlib
import json
import os

import fakeredis.aioredis
import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from routeopt.models import Base
from routeopt.modules.orders.geocoding import Geocoder, GeocodeResult


@pytest.fixture(autouse=True)
def _no_rate_limit(monkeypatch):
    # Don't actually sleep for the Nominatim rate limit in tests.
    monkeypatch.setattr("routeopt.modules.orders.geocoding.settings.nominatim_rate_limit_s", 0)


@pytest.fixture
def redis_client():
    return fakeredis.aioredis.FakeRedis(decode_responses=True)


def _cache_key(address: str) -> str:
    return f"geo:{hashlib.sha256(address.lower().strip().encode()).hexdigest()}"


async def test_cache_hit_skips_http(redis_client, monkeypatch):
    address = "12 Rue Didouche Mourad, Alger"
    await redis_client.set(
        _cache_key(address), json.dumps({"lat": 36.75, "lon": 3.06, "status": "matched"})
    )

    async def _boom(self, addr):  # noqa: ANN001
        raise AssertionError("_search should not be called on a cache hit")

    monkeypatch.setattr(Geocoder, "_search", _boom)
    result = await Geocoder(redis_client).geocode(address)
    assert result == GeocodeResult(36.75, 3.06, "matched")


async def test_house_level_is_matched_and_cached(redis_client, monkeypatch):
    async def _search(self, addr):  # noqa: ANN001
        return [{"lat": "36.7538", "lon": "3.0588", "place_rank": 30}]

    monkeypatch.setattr(Geocoder, "_search", _search)
    result = await Geocoder(redis_client).geocode("12 Rue Didouche Mourad")
    assert result.status == "matched"
    assert result.lat == pytest.approx(36.7538)
    # cached for next time
    assert await redis_client.get(_cache_key("12 Rue Didouche Mourad")) is not None


async def test_street_level_is_approximate(redis_client, monkeypatch):
    async def _search(self, addr):  # noqa: ANN001
        return [{"lat": "36.75", "lon": "3.06", "place_rank": 26}]

    monkeypatch.setattr(Geocoder, "_search", _search)
    result = await Geocoder(redis_client).geocode("Rue quelque part")
    assert result.status == "approximate"


async def test_no_result_is_failed_and_cached(redis_client, monkeypatch):
    async def _search(self, addr):  # noqa: ANN001
        return []

    monkeypatch.setattr(Geocoder, "_search", _search)
    result = await Geocoder(redis_client).geocode("nowhere at all")
    assert result.status == "failed"
    assert result.lat is None
    assert await redis_client.get(_cache_key("nowhere at all")) is not None


async def test_network_error_is_failed_but_not_cached(redis_client, monkeypatch):
    async def _search(self, addr):  # noqa: ANN001
        raise httpx.ConnectError("nominatim down")

    monkeypatch.setattr(Geocoder, "_search", _search)
    result = await Geocoder(redis_client).geocode("12 Rue Didouche")
    assert result.status == "failed"
    # transient failure must NOT poison the cache
    assert await redis_client.get(_cache_key("12 Rue Didouche")) is None


# ── DB-backed: bulk_create geocodes address-only rows ────────────────────────
TEST_DB_URL = os.getenv("TEST_DATABASE_URL")


class _FakeGeocoder:
    """Deterministic geocoder: known addresses match, 'unknown' fails."""

    async def geocode(self, address: str) -> GeocodeResult:
        if "unknown" in address.lower():
            return GeocodeResult(None, None, "failed")
        return GeocodeResult(36.75, 3.06, "matched")


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False)() as s:
        yield s
    await engine.dispose()


@pytest.mark.skipif(not TEST_DB_URL, reason="TEST_DATABASE_URL not set")
async def test_bulk_create_geocodes_address_only(session):
    import uuid

    from routeopt.models.company import Company
    from routeopt.modules.orders.schemas import DeliveryIn
    from routeopt.modules.orders.service import OrdersService

    company = Company(name="Acme")
    session.add(company)
    await session.flush()
    company_id = str(company.id)

    service = OrdersService(session, geocoder=_FakeGeocoder())
    created = await service.bulk_create(
        company_id,
        [
            DeliveryIn(address="12 Rue Didouche Mourad, Alger"),  # geocodes -> matched
            DeliveryIn(address="unknown place"),  # fails -> pending
            DeliveryIn(address="Pre-geocoded", lat=36.8, lon=3.1),  # coords kept
        ],
    )

    by_addr = {d.address: d for d in created}
    assert by_addr["12 Rue Didouche Mourad, Alger"].geocoding_status == "matched"
    assert by_addr["12 Rue Didouche Mourad, Alger"].status == "geocoded"
    assert by_addr["unknown place"].geocoding_status == "failed"
    assert by_addr["unknown place"].status == "pending"
    assert float(by_addr["Pre-geocoded"].lat) == pytest.approx(36.8)

    # Only the geocoded ones are routable (2 of 3)
    routable = await service.list_routable(company_id)
    assert len(routable) == 2
    assert uuid.UUID(company_id)  # sanity
