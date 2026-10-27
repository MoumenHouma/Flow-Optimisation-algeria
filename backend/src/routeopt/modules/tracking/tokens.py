"""Stateless signed tokens for public delivery tracking (F18).

A tracking link carries ``{delivery_id}.{sig}`` where sig is an HMAC of the
delivery id under the app secret. No DB column, no per-link state — the token is
self-verifying, so a leaked link exposes only one delivery's public status and
never any PII in the URL (PRD §4.2 data protection).
"""

import hmac

from routeopt.config import get_settings
from routeopt.core.webhooks import sign

settings = get_settings()


def make_token(delivery_id: str) -> str:
    return f"{delivery_id}.{sign(settings.secret_key, delivery_id)}"


def verify_token(token: str) -> str | None:
    """Return the delivery id if the token is authentic, else None."""
    delivery_id, _, provided = token.partition(".")
    if not delivery_id or not provided:
        return None
    expected = sign(settings.secret_key, delivery_id)
    if not hmac.compare_digest(provided, expected):
        return None
    return delivery_id
