"""Orders logic: bulk import + geocoding (F1, F2).

Geocoding uses Nominatim with an aggressive Redis cache (geo:{hash}, 30d —
docs/SCHEMA.md §7) and tolerates approximate matches (PRD §4.1, §4.3).
"""

import hashlib

from routeopt.redis_client import redis_client


class OrdersService:
    async def geocode(self, address: str) -> tuple[float | None, float | None, str]:
        """Return (lat, lon, status). status ∈ matched|approximate|failed."""
        cache_key = f"geo:{hashlib.sha256(address.encode()).hexdigest()}"
        cached = await redis_client.get(cache_key)
        if cached:
            lat, lon, status = cached.split("|")
            return (float(lat) if lat else None, float(lon) if lon else None, status)
        # TODO: call Nominatim (settings.nominatim_url), map confidence -> status,
        # then cache with TTL=30d. Return failed on no result.
        raise NotImplementedError("geocode: call Nominatim and cache result")

    async def bulk_import(self, rows: list[dict]) -> dict:
        # TODO: validate rows, geocode each, persist Delivery records, return summary.
        raise NotImplementedError("bulk_import: validate + geocode + persist")
