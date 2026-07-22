"""Audit-log DTOs (H2)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditEntryOut(BaseModel):
    id: int
    action: str
    resource_type: str
    resource_id: str | None
    actor_user_id: str | None
    metadata: dict[str, Any]
    ip_address: str | None
    created_at: datetime

    @classmethod
    def from_model(cls, e: Any) -> "AuditEntryOut":
        return cls(
            id=e.id,
            action=e.action,
            resource_type=e.resource_type,
            resource_id=str(e.resource_id) if e.resource_id else None,
            actor_user_id=str(e.actor_user_id) if e.actor_user_id else None,
            metadata=e.audit_metadata,
            ip_address=str(e.ip_address) if e.ip_address is not None else None,
            created_at=e.created_at,
        )
