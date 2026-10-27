"""Customer-notification providers (F18).

Sending is abstracted so a real SMS/WhatsApp gateway can be plugged in without
touching the enqueue/consumer path. Algeria's market is WhatsApp-heavy; the
default is a no-op (dev/tests never send), with a logging variant for staging.
"""

import logging
from typing import Protocol

logger = logging.getLogger("routeopt.notifications")


class SmsProvider(Protocol):
    name: str

    async def send(self, to: str, body: str) -> None:
        """Deliver a message to a phone number. Must not raise on best-effort paths."""
        ...


class NoOpProvider:
    """Swallow messages — the default so dev and tests never contact a gateway."""

    name = "noop"

    async def send(self, to: str, body: str) -> None:  # noqa: D102
        return None


class LogProvider:
    """Log messages instead of sending — useful in staging to eyeball output."""

    name = "log"

    async def send(self, to: str, body: str) -> None:  # noqa: D102
        logger.info("notify %s: %s", to, body)


def get_provider(name: str) -> SmsProvider:
    providers: dict[str, SmsProvider] = {"noop": NoOpProvider(), "log": LogProvider()}
    return providers.get(name, NoOpProvider())
