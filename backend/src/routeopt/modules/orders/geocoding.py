"""Address geocoding via Nominatim with aggressive Redis caching (F2).

Results are cached under ``geo:{sha256(address)}`` for 30 days (SCHEMA.md §7),
biased to Algeria, and tolerant of imprecise addresses (PRD §4.1, §4.3): a
street- or area-level hit is returned as ``approximate`` rather than discarded.

Failures are classified but only *definitive* ones (Nominatim returned no match)
are cached — transient network errors return ``failed`` without poisoning the
cache, so a later retry can succeed.
"""

import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

import httpx
import redis.asyncio as redis

from routeopt.config import get_settings

settings = get_settings()

# Nominatim place_rank: 30 = house/building, ~26 = street, lower = area.
_HOUSE_LEVEL_RANK = 30


@dataclass
class GeocodeResult:
    lat: float | None
    lon: float | None
    status: str  # matched | approximate | failed


class Geocoder:
    def __init__(self, redis_client: redis.Redis, base_url: str | None = None) -> None:
        self.redis = redis_client
        self.base_url = (base_url or settings.nominatim_url).rstrip("/")

    async def geocode(self, address: str) -> GeocodeResult:
        cache_key = f"geo:{hashlib.sha256(address.lower().strip().encode()).hexdigest()}"
        cached = await self.redis.get(cache_key)
        if cached:
            return GeocodeResult(**json.loads(cached))

        try:
            raw = await self._search(address)
        except httpx.HTTPError:
            # Transient failure — do not cache, allow later retry.
            return GeocodeResult(None, None, "failed")

        result = self._to_result(raw)
        await self.redis.set(
            cache_key, json.dumps(asdict(result)), ex=settings.geocoding_cache_ttl_s
        )
        if settings.nominatim_rate_limit_s:
            await asyncio.sleep(settings.nominatim_rate_limit_s)
        return result

    async def _search(self, address: str) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {
            "q": address,
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 1,
            "countrycodes": settings.nominatim_country,
        }
        headers = {"User-Agent": settings.nominatim_user_agent}
        async with httpx.AsyncClient(timeout=10, headers=headers) as client:
            resp = await client.get(f"{self.base_url}/search", params=params)
            resp.raise_for_status()
            data: list[dict[str, Any]] = resp.json()
            return data

    @staticmethod
    def _to_result(raw: list[dict[str, Any]]) -> GeocodeResult:
        if not raw:
            return GeocodeResult(None, None, "failed")
        best = raw[0]
        place_rank = int(best.get("place_rank", 0))
        status = "matched" if place_rank >= _HOUSE_LEVEL_RANK else "approximate"
        return GeocodeResult(lat=float(best["lat"]), lon=float(best["lon"]), status=status)
