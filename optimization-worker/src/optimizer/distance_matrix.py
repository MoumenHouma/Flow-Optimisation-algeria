"""Distance matrix builder via OSRM /table with Redis caching.

Cache key is a hash of the ordered coordinates (docs/SCHEMA.md §7, dm:{hash},
TTL 24h). Falls back to a great-circle approximation when OSRM is unreachable or
returns an error (ARCHITECTURE §2.4, PRD §4.3).
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

import httpx
import redis.asyncio as redis

from optimizer.config import get_settings
from optimizer.models import GeoPoint

settings = get_settings()

# Great-circle fallback speed when OSRM is unavailable (~30 km/h urban Algeria).
_FALLBACK_SPEED_MPS = 8.33
_EARTH_RADIUS_M = 6_371_000


class OSRMError(Exception):
    """OSRM was reachable but returned an unusable response."""


class OSRMTimeoutError(OSRMError):
    """OSRM did not respond in time."""


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
    """Build an NxN duration+distance matrix from OSRM /table, caching the result.

    Raises OSRMError (incl. OSRMTimeoutError) on any transport/protocol failure so
    the caller can fall back. Unroutable cells (OSRM returns ``null``) are
    backfilled with a great-circle estimate rather than failing the whole matrix.
    """
    osrm_url = (osrm_url or settings.osrm_url).rstrip("/")
    cache_key = f"dm:{_coords_hash(points)}"

    cached = await redis_client.get(cache_key)
    if cached:
        data = json.loads(cached)
        return DistanceMatrix(durations=data["durations"], distances=data["distances"])

    coords = ";".join(f"{p.lon},{p.lat}" for p in points)  # OSRM expects lon,lat
    url = f"{osrm_url}/table/v1/driving/{coords}"
    params = {"annotations": "duration,distance"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
    except httpx.TimeoutException as exc:
        raise OSRMTimeoutError(f"OSRM timed out for {len(points)} points") from exc
    except httpx.HTTPError as exc:
        raise OSRMError(f"OSRM request failed: {exc}") from exc

    body = resp.json()
    if body.get("code") != "Ok":
        raise OSRMError(f"OSRM returned code={body.get('code')!r}")
    if "durations" not in body or "distances" not in body:
        raise OSRMError("OSRM response missing durations/distances")

    matrix = DistanceMatrix(
        durations=_backfill_nulls(body["durations"], points, is_distance=False),
        distances=_backfill_nulls(body["distances"], points, is_distance=True),
    )
    await redis_client.set(
        cache_key,
        json.dumps({"durations": matrix.durations, "distances": matrix.distances}),
        ex=settings.distance_matrix_ttl_s,
    )
    return matrix


def _backfill_nulls(
    matrix: list[list[float | None]], points: list[GeoPoint], *, is_distance: bool
) -> list[list[float]]:
    """Replace OSRM ``null`` entries (unroutable pairs) with a great-circle estimate."""
    out: list[list[float]] = []
    for i, row in enumerate(matrix):
        filled: list[float] = []
        for j, value in enumerate(row):
            if value is not None:
                filled.append(float(value))
            else:
                d = _haversine_m(points[i], points[j])
                filled.append(d if is_distance else d / _FALLBACK_SPEED_MPS)
        out.append(filled)
    return out


def _haversine_m(a: GeoPoint, b: GeoPoint) -> float:
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlon = math.radians(b.lon - a.lon)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.asin(math.sqrt(h))


def haversine_matrix(points: list[GeoPoint]) -> DistanceMatrix:
    """Great-circle NxN matrix — approximation used when OSRM is unreachable.

    OSM coverage in Algeria is uneven (PRD §4.3), so a road-network miss falls
    back to straight-line distance rather than failing the whole optimization.
    """
    n = len(points)
    distances = [[0.0] * n for _ in range(n)]
    durations = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = _haversine_m(points[i], points[j])
            distances[i][j] = distances[j][i] = d
            durations[i][j] = durations[j][i] = d / _FALLBACK_SPEED_MPS
    return DistanceMatrix(durations=durations, distances=distances)


async def build_matrix_with_fallback(
    points: list[GeoPoint],
    redis_client: redis.Redis,
    osrm_url: str | None = None,
) -> tuple[DistanceMatrix, bool]:
    """Return (matrix, used_osrm). Falls back to haversine on any OSRM failure."""
    try:
        return await build_distance_matrix(points, redis_client, osrm_url), True
    except Exception:  # noqa: BLE001 - OSRM down/unreachable/error -> approximate
        return haversine_matrix(points), False


async def osrm_healthy(osrm_url: str | None = None, timeout: float = 5.0) -> bool:
    """Cheap OSRM reachability probe (two dummy points near Alger)."""
    osrm_url = (osrm_url or settings.osrm_url).rstrip("/")
    url = f"{osrm_url}/table/v1/driving/3.0588,36.7538;3.06,36.75"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return bool(resp.json().get("code") == "Ok")
    except (httpx.HTTPError, ValueError):
        return False


async def osrm_route_geometry(
    points: list[GeoPoint], osrm_url: str | None = None
) -> dict[str, Any] | None:
    """Return the road-path GeoJSON LineString for an ordered point list, or None.

    Calls OSRM /route with overview=full & geometries=geojson. Any failure
    (OSRM down, non-Ok, malformed) returns None so the caller keeps the
    straight-line fallback — never fails the optimization over a missing map path.
    """
    if len(points) < 2:
        return None
    osrm_url = (osrm_url or settings.osrm_url).rstrip("/")
    coords = ";".join(f"{p.lon},{p.lat}" for p in points)
    url = f"{osrm_url}/route/v1/driving/{coords}"
    params = {"overview": "full", "geometries": "geojson"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            body = resp.json()
        if body.get("code") != "Ok" or not body.get("routes"):
            return None
        geometry = body["routes"][0].get("geometry")
        return geometry if isinstance(geometry, dict) else None
    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        return None
