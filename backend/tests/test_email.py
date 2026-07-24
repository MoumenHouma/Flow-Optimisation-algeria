"""Unit tests for the transactional-email layer (no DB, no network).

The password-reset flow test (test_password_reset.py) patches send_password_reset
out, so these cover core/email.py directly: provider selection, link building,
and the best-effort send that must never raise.
"""

import logging

from routeopt.core import email


def test_get_provider_selects_by_name() -> None:
    assert email.get_provider("noop").name == "noop"
    assert email.get_provider("log").name == "log"
    assert email.get_provider("smtp").name == "smtp"
    # Unknown provider falls back to the silent no-op, never an error.
    assert email.get_provider("does-not-exist").name == "noop"


def test_reset_link_uses_public_base_url(monkeypatch) -> None:
    monkeypatch.setattr(email.settings, "public_base_url", "https://app.routeopt.dz/")
    link = email.reset_link("abc123")
    # Trailing slash collapsed, token carried in the query string.
    assert link == "https://app.routeopt.dz/reset-password?token=abc123"


async def test_noop_provider_sends_nothing() -> None:
    # Should complete without side effects or errors.
    assert await email.NoOpProvider().send("x@y.dz", "s", "b") is None


async def test_log_provider_emits_a_record(caplog) -> None:
    with caplog.at_level(logging.INFO, logger="routeopt.email"):
        await email.LogProvider().send("x@y.dz", "Sujet", "Corps")
    assert any("x@y.dz" in r.message for r in caplog.records)


async def test_send_password_reset_uses_configured_provider(monkeypatch) -> None:
    sent: list[tuple[str, str, str]] = []

    class Capture:
        name = "capture"

        async def send(self, to: str, subject: str, body: str) -> None:
            sent.append((to, subject, body))

    monkeypatch.setattr(email, "get_provider", lambda name: Capture())
    monkeypatch.setattr(email.settings, "public_base_url", "https://app.routeopt.dz")
    await email.send_password_reset("gerant@flotte.dz", "tok-xyz")

    assert len(sent) == 1
    to, subject, body = sent[0]
    assert to == "gerant@flotte.dz"
    assert "réinitialisation" in subject.lower()
    assert "https://app.routeopt.dz/reset-password?token=tok-xyz" in body


async def test_send_password_reset_swallows_provider_errors(monkeypatch, caplog) -> None:
    """A relay failure must not propagate to the caller (best-effort delivery)."""

    class Boom:
        name = "boom"

        async def send(self, to: str, subject: str, body: str) -> None:
            raise RuntimeError("relay down")

    monkeypatch.setattr(email, "get_provider", lambda name: Boom())
    with caplog.at_level(logging.ERROR, logger="routeopt.email"):
        # Must return normally despite the provider raising.
        await email.send_password_reset("x@y.dz", "tok")
    assert any("delivery failed" in r.message for r in caplog.records)
