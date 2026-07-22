"""Audit trail helper (H2 — CNIL loi 18-07, docs/ARCHITECTURE.md §5.2).

`record()` appends one immutable row to `audit_log` for a sensitive action.
It never raises into the caller: an audit-write failure must not break the
business action it accompanies, so errors are swallowed (and would surface via
Sentry/logs). Callers pass the already-open request session; the row is flushed
but not committed here — it rides the caller's transaction.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.models.audit_log import AuditLog

logger = logging.getLogger("routeopt.audit")


def client_ip(request: Request) -> str | None:
    """Best-effort caller IP, honouring a single X-Forwarded-For hop."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _as_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None


async def record(
    session: AsyncSession,
    *,
    action: str,
    resource_type: str,
    company_id: str | uuid.UUID | None = None,
    actor_user_id: str | uuid.UUID | None = None,
    resource_id: str | uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    """Append an audit entry. Best-effort — a failure here never breaks the action."""
    try:
        session.add(
            AuditLog(
                company_id=_as_uuid(company_id),
                actor_user_id=_as_uuid(actor_user_id),
                action=action,
                resource_type=resource_type,
                resource_id=_as_uuid(resource_id),
                audit_metadata=metadata or {},
                ip_address=ip_address,
            )
        )
        await session.flush()
    except Exception:  # pragma: no cover - audit must never break the caller
        logger.exception("audit.record failed", extra={"action": action})
