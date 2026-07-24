"""Password-recovery flow against a real Postgres (same harness as test_auth_flow).

The email provider is forced to a capture double, so the clear token never has to
be scraped from a log. Skipped unless TEST_DATABASE_URL is set.
"""

import os

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from routeopt.core import email as email_module
from routeopt.database import get_session
from routeopt.main import app
from routeopt.models import Base

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB_URL, reason="TEST_DATABASE_URL not set")


@pytest.fixture
def sent_tokens(monkeypatch):
    """Capture the reset tokens the service would have emailed."""
    captured: list[tuple[str, str]] = []

    async def _capture(to: str, token: str) -> None:
        captured.append((to, token))

    # The service imported the symbol directly, so patch it there too.
    monkeypatch.setattr(email_module, "send_password_reset", _capture)
    monkeypatch.setattr("routeopt.modules.auth.service.send_password_reset", _capture)
    return captured


@pytest_asyncio.fixture
async def client(monkeypatch):
    # The IP throttle on the recovery endpoints talks to Redis; the module-level
    # real client would stay bound to the first test's event loop (test_rate_limit
    # does the same substitution).
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("routeopt.core.dependencies.redis_client", fake)

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


async def _register(client: AsyncClient, email: str, password: str = "supersecret") -> dict:
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "company_name": "Acme Logistics",
            "email": email,
            "password": password,
            "full_name": "Khaled",
        },
    )
    assert reg.status_code == 201, reg.text
    return reg.json()


async def test_reset_password_end_to_end(client: AsyncClient, sent_tokens) -> None:
    tokens = await _register(client, "reset@acme.dz")

    asked = await client.post("/api/v1/auth/forgot-password", json={"email": "reset@acme.dz"})
    assert asked.status_code == 202
    assert len(sent_tokens) == 1
    to, reset_token = sent_tokens[0]
    assert to == "reset@acme.dz"

    done = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "password": "brand-new-secret"},
    )
    assert done.status_code == 204

    # Old password rejected, new one accepted.
    old = await client.post(
        "/api/v1/auth/login", json={"email": "reset@acme.dz", "password": "supersecret"}
    )
    assert old.status_code == 401
    new = await client.post(
        "/api/v1/auth/login",
        json={"email": "reset@acme.dz", "password": "brand-new-secret"},
    )
    assert new.status_code == 200

    # Every pre-reset session is dead, not just the current family.
    stale = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert stale.status_code == 401


async def test_reset_token_is_single_use(client: AsyncClient, sent_tokens) -> None:
    await _register(client, "once@acme.dz")
    await client.post("/api/v1/auth/forgot-password", json={"email": "once@acme.dz"})
    _, reset_token = sent_tokens[0]

    first = await client.post(
        "/api/v1/auth/reset-password", json={"token": reset_token, "password": "first-secret"}
    )
    assert first.status_code == 204
    replayed = await client.post(
        "/api/v1/auth/reset-password", json={"token": reset_token, "password": "second-secret"}
    )
    assert replayed.status_code == 401


async def test_using_one_link_voids_the_others(client: AsyncClient, sent_tokens) -> None:
    """Two requests in a row: consuming the newer link kills the older one."""
    await _register(client, "twice@acme.dz")
    await client.post("/api/v1/auth/forgot-password", json={"email": "twice@acme.dz"})
    await client.post("/api/v1/auth/forgot-password", json={"email": "twice@acme.dz"})
    assert len(sent_tokens) == 2
    older, newer = sent_tokens[0][1], sent_tokens[1][1]

    used = await client.post(
        "/api/v1/auth/reset-password", json={"token": newer, "password": "newer-secret"}
    )
    assert used.status_code == 204
    stale = await client.post(
        "/api/v1/auth/reset-password", json={"token": older, "password": "older-secret"}
    )
    assert stale.status_code == 401


async def test_expired_token_is_rejected(client: AsyncClient, sent_tokens, monkeypatch) -> None:
    from routeopt.modules.auth import service as auth_service

    monkeypatch.setattr(auth_service.settings, "password_reset_expire_minutes", -1)
    await _register(client, "expired@acme.dz")
    await client.post("/api/v1/auth/forgot-password", json={"email": "expired@acme.dz"})
    _, reset_token = sent_tokens[0]

    refused = await client.post(
        "/api/v1/auth/reset-password", json={"token": reset_token, "password": "too-late-secret"}
    )
    assert refused.status_code == 401


async def test_unknown_email_still_202_and_sends_nothing(client: AsyncClient, sent_tokens) -> None:
    """No user enumeration: the response is identical for an unknown address."""
    asked = await client.post("/api/v1/auth/forgot-password", json={"email": "nobody@acme.dz"})
    assert asked.status_code == 202
    assert sent_tokens == []


async def test_garbage_token_is_rejected(client: AsyncClient) -> None:
    refused = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "x" * 32, "password": "irrelevant-secret"},
    )
    assert refused.status_code == 401
