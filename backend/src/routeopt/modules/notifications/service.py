"""Customer notifications (F18): enqueue on status change, drain in the background.

The status-change path only ever does a non-blocking Redis ``LPUSH`` (so the
driver's action never waits on an SMS gateway — §4.1 intermittent connectivity).
A background consumer, started from the app lifespan, drains the queue and calls
the provider. Tests assert the item lands in Redis, not that a message was sent.
"""

import json
import logging

import redis.asyncio as redis

from routeopt.config import get_settings
from routeopt.modules.notifications.providers import get_provider

logger = logging.getLogger("routeopt.notifications")
settings = get_settings()


async def enqueue(redis_client: redis.Redis, *, to: str, body: str, kind: str) -> None:
    """Queue one customer message. Best-effort and non-blocking on the hot path."""
    payload = json.dumps({"to": to, "body": body, "kind": kind})
    await redis_client.lpush(settings.notify_queue, payload)


def build_message(*, status: str, tracking_url: str) -> str | None:
    """The customer-facing text for a delivery status, or None if we don't notify."""
    if status == "en_route":
        return f"Votre colis arrive bientôt. Suivez la livraison : {tracking_url}"
    if status == "delivered":
        return "Votre colis a été livré. Merci !"
    return None


async def run_consumer(redis_client: redis.Redis) -> None:
    """Drain the notification queue forever, sending via the configured provider."""
    provider = get_provider(settings.sms_provider)
    logger.info("notification consumer started (provider=%s)", provider.name)
    while True:
        item = await redis_client.blpop([settings.notify_queue], timeout=5)
        if item is None:
            continue
        _, raw = item
        try:
            msg = json.loads(raw)
            await provider.send(msg["to"], msg["body"])
        except Exception as exc:  # noqa: BLE001 - a bad message must not kill the loop
            logger.warning("notification send failed: %s", exc)
