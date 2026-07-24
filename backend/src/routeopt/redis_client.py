"""Shared Redis client — cache, queue and sessions (docs/SCHEMA.md §7)."""

import redis.asyncio as redis

from routeopt.config import get_settings

settings = get_settings()

redis_client: redis.Redis = redis.from_url(settings.redis_url, decode_responses=True)
