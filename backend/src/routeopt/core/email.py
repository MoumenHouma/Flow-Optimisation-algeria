"""Transactional email — providers + the password-reset message.

Same shape as the notification providers (`modules/notifications/providers.py`):
the transport is abstracted so a real relay plugs in without touching callers.
The default is a no-op (dev and tests never send); ``log`` prints the message —
which is how a self-hosted deployment without SMTP can still recover an account
from the backend log. SMTP uses stdlib ``smtplib`` in a worker thread, so no
extra dependency is pulled in.
"""

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from routeopt.config import get_settings

logger = logging.getLogger("routeopt.email")
settings = get_settings()


class EmailProvider(Protocol):
    name: str

    async def send(self, to: str, subject: str, body: str) -> None:
        """Deliver a plain-text email. Must not raise on best-effort paths."""
        ...


class NoOpProvider:
    """Swallow email — the default so tests never contact a relay."""

    name = "noop"

    async def send(self, to: str, subject: str, body: str) -> None:  # noqa: D102
        return None


class LogProvider:
    """Log the message instead of sending it (dev, and SMTP-less deployments)."""

    name = "log"

    async def send(self, to: str, subject: str, body: str) -> None:  # noqa: D102
        logger.info("email to=%s subject=%s\n%s", to, subject, body)


class SmtpProvider:
    """Send through an SMTP relay (stdlib smtplib, run off the event loop)."""

    name = "smtp"

    async def send(self, to: str, subject: str, body: str) -> None:  # noqa: D102
        await asyncio.to_thread(self._send_blocking, to, subject, body)

    def _send_blocking(self, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = settings.email_from
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)


def get_provider(name: str) -> EmailProvider:
    providers: dict[str, EmailProvider] = {
        "noop": NoOpProvider(),
        "log": LogProvider(),
        "smtp": SmtpProvider(),
    }
    return providers.get(name, NoOpProvider())


def reset_link(token: str) -> str:
    return f"{settings.public_base_url.rstrip('/')}/reset-password?token={token}"


async def send_password_reset(to: str, token: str) -> None:
    """Best-effort delivery of a reset link — never breaks the request."""
    link = reset_link(token)
    minutes = settings.password_reset_expire_minutes
    body = (
        "Bonjour,\n\n"
        "Vous avez demandé la réinitialisation de votre mot de passe RouteOpt.\n"
        f"Ouvrez ce lien pour choisir un nouveau mot de passe (valable {minutes} minutes) :\n\n"
        f"{link}\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message : "
        "votre mot de passe reste inchangé.\n\n"
        "— RouteOpt\n"
    )
    try:
        await get_provider(settings.email_provider).send(
            to, "RouteOpt — réinitialisation de votre mot de passe", body
        )
    except Exception:  # noqa: BLE001 - delivery failure must not leak to the caller
        logger.exception("password-reset email delivery failed for %s", to)
