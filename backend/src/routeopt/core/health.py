"""Readiness checks for dependencies (docs/ARCHITECTURE.md §6).

OSRM is treated as non-fatal for readiness: the optimization worker falls back
to a great-circle approximation when it's unreachable (PRD §4.3), so the API is
still usable — the probe reports it as ``unreachable`` rather than failing.
"""

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.config import get_settings
from routeopt.redis_client import redis_client

settings = get_settings()


async def check_database(session: AsyncSession) -> bool:
    try:
        await session.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def check_redis() -> bool:
    try:
        return bool(await redis_client.ping())
    except Exception:
        return False


async def check_osrm() -> bool:
    url = f"{settings.osrm_url.rstrip('/')}/table/v1/driving/3.06,36.75;3.07,36.76"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return bool(resp.json().get("code") == "Ok")
    except Exception:
        return False
