"""Audit-log read service (H2). Writes go through core/audit.record."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.models.audit_log import AuditLog


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_entries(
        self, company_id: str, *, action: str | None = None, limit: int = 100
    ) -> list[AuditLog]:
        """Most-recent audit entries for the company, newest first."""
        stmt = select(AuditLog).where(AuditLog.company_id == uuid.UUID(company_id))
        if action:
            stmt = stmt.where(AuditLog.action == action)
        stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit)
        return list(await self.session.scalars(stmt))
