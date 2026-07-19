"""Distance matrix builder via OSRM /table with Redis caching.

Cache key is a hash of the ordered coordinates (docs/SCHEMA.md §7, dm:{hash},
TTL 24h). Falls back to recompute on cache miss (ARCHITECTURE §4.2 L4).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import httpx
import redis.asyncio as redis

from optimizer.config import get_settings
from optimizer.models import GeoPoint

settings = get_settings()


class OSRMTimeoutError(Exception):
    pass


@dataclass
class DistanceMatrix:
    durations: list[list[float]]  # seconds, NxN
    distances: list[list[float]]  # meters, NxN


def _coords_hash(points: list[GeoPoint]) -> str:
    raw = ";".join(f"{p.lat:.6f},{p.lon:.6f}" for p in points)
    return hashlib.sha256(raw.encode()).hexdigest()


async def build_distance_matrix(
    points: list[GeoPoint],
    redis_client: redis.Redis,
    osrm_url: str | None = None,
) -> DistanceMatrix:
    """Build an NxN duration+distance matrix, caching the result in Redis."""
    osrm_url = osrm_url or settings.osrm_url
    cache_key = f"dm:{_coords_hash(points)}"

    cached = await redis_client.get(cache_key)
    if cached:
        data = json.loads(cached)
        return DistanceMatrix(durations=data["durations"], distances=data["distances"])

    coords = ";".join(f"{p.lon},{p.lat}" for p in points)  # OSRM is lon,lat
    url = f"{osrm_url}/table/v1/driving/{coords}"
    params = {"annotations": "duration,distance"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
    except httpx.TimeoutException as exc:  # pragma: no cover
        raise OSRMTimeoutError(f"OSRM table request timed out for {len(points)} points") from exc

    body = resp.json()
    matrix = DistanceMatrix(durations=body["durations"], distances=body["distances"])
    await redis_client.set(
        cache_key,
        json.dumps({"durations": matrix.durations, "distances": matrix.distances}),
        ex=settings.distance_matrix_ttl_s,
    )
    return matrix
