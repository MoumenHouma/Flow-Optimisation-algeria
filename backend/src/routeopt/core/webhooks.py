"""Outbound webhook dispatch (F10).

On a domain event, POST a signed JSON payload to every active webhook that
subscribed to it. Delivery is best-effort and isolated: a failing endpoint never
breaks the request that produced the event. The body is signed with the
webhook's secret (HMAC-SHA256) so receivers can verify authenticity.

Note: dispatch is awaited inline for simplicity — a high-volume deployment would
move this to a queue with retries.
"""

import hashlib
import hmac
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.models.webhook import Webhook

logger = logging.getLogger("routeopt.webhooks")

_TIMEOUT_S = 5.0


def sign(secret: str, body: str) -> str:
    """HMAC-SHA256 hex signature of the raw body, as sent in X-RouteOpt-Signature."""
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


async def _post(url: str, event: str, body: str, secret: str) -> None:
    """Deliver one webhook. Best-effort — network/HTTP errors are swallowed."""
    headers = {
        "Content-Type": "application/json",
        "X-RouteOpt-Event": event,
        "X-RouteOpt-Signature": f"sha256={sign(secret, body)}",
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_S) as client:
            await client.post(url, content=body, headers=headers)
    except httpx.HTTPError as exc:  # pragma: no cover - network failure path
        logger.warning("webhook delivery failed url=%s event=%s err=%s", url, event, exc)


def _subscribes(webhook: Webhook, event: str) -> bool:
    wanted = {e.strip() for e in webhook.events.split(",") if e.strip()}
    return "*" in wanted or event in wanted


class WebhookDispatcher:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def dispatch(self, company_id: str, event: str, data: dict[str, Any]) -> int:
        """Send `event` to every active, subscribed webhook. Returns count sent."""
        rows = await self.session.scalars(
            select(Webhook).where(
                Webhook.company_id == uuid.UUID(company_id),
                Webhook.active.is_(True),
            )
        )
        targets = [w for w in rows if _subscribes(w, event)]
        if not targets:
            return 0

        payload = {
            "id": str(uuid.uuid4()),
            "event": event,
            "created_at": datetime.now(UTC).isoformat(),
            "data": data,
        }
        body = json.dumps(payload, separators=(",", ":"))
        for w in targets:
            await _post(w.url, event, body, w.secret)
        return len(targets)
