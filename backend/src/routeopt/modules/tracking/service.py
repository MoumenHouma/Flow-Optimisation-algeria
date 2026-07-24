"""Live tracking (F18): Redis-backed vehicle positions + public delivery status.

Positions live only in Redis, keyed per company so a dispatcher's stream can
never surface another tenant's fleet. Keys expire on their own (stale drivers
drop off the map); the per-company vehicle set is cleaned lazily on read.
"""

import json
import time
import uuid

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.config import get_settings
from routeopt.models.delivery import Delivery
from routeopt.models.route import Route
from routeopt.modules.tracking.schemas import PositionOut, TrackOut
from routeopt.modules.tracking.tokens import verify_token

settings = get_settings()


def _pos_key(company_id: str, vehicle_id: str) -> str:
    return f"live:pos:{company_id}:{vehicle_id}"


def _set_key(company_id: str) -> str:
    return f"live:vehicles:{company_id}"


async def write_position(
    redis_client: redis.Redis, company_id: str, vehicle_id: str, lat: float, lon: float
) -> None:
    """Record a vehicle's current position (short TTL) + track it for its company."""
    payload = json.dumps({"lat": lat, "lon": lon, "ts": time.time()})
    await redis_client.set(
        _pos_key(company_id, vehicle_id), payload, ex=settings.live_position_ttl_s
    )
    await redis_client.sadd(_set_key(company_id), vehicle_id)


async def read_positions(redis_client: redis.Redis, company_id: str) -> list[PositionOut]:
    """Live positions for a company's fleet; prunes expired vehicles from the set."""
    vehicle_ids = await redis_client.smembers(_set_key(company_id))
    positions: list[PositionOut] = []
    for raw_vid in vehicle_ids:
        vid = raw_vid.decode() if isinstance(raw_vid, bytes) else str(raw_vid)
        raw = await redis_client.get(_pos_key(company_id, vid))
        if raw is None:
            await redis_client.srem(_set_key(company_id), vid)  # expired — forget it
            continue
        data = json.loads(raw)
        positions.append(
            PositionOut(vehicle_id=vid, lat=data["lat"], lon=data["lon"], ts=data["ts"])
        )
    return positions


class TrackingService:
    def __init__(self, session: AsyncSession, redis_client: redis.Redis) -> None:
        self.session = session
        self.redis = redis_client

    async def public_track(self, token: str) -> TrackOut | None:
        """Resolve a signed tracking token to a delivery's public status + ETA dot."""
        delivery_id = verify_token(token)
        if delivery_id is None:
            return None
        delivery = await self.session.get(Delivery, uuid.UUID(delivery_id))
        if delivery is None or delivery.deleted_at is not None:
            return None

        position: PositionOut | None = None
        if delivery.route_id is not None and delivery.status in ("assigned", "en_route"):
            route = await self.session.get(Route, delivery.route_id)
            if route is not None and route.vehicle_id is not None:
                raw = await self.redis.get(
                    _pos_key(str(delivery.company_id), str(route.vehicle_id))
                )
                if raw is not None:
                    d = json.loads(raw)
                    position = PositionOut(
                        vehicle_id=str(route.vehicle_id), lat=d["lat"], lon=d["lon"], ts=d["ts"]
                    )
        return TrackOut(
            order_id=delivery.order_id, status=delivery.status, vehicle_position=position
        )
