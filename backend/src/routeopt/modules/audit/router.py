"""Audit-log endpoint (H2) — admin-only read of the company's audit trail."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.dependencies import CurrentUser, require_roles
from routeopt.database import get_session
from routeopt.modules.audit.schemas import AuditEntryOut
from routeopt.modules.audit.service import AuditService

router = APIRouter(prefix="/audit-log", tags=["audit"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
AdminDep = Annotated[CurrentUser, Depends(require_roles("admin"))]


@router.get("", response_model=list[AuditEntryOut])
async def list_audit_log(
    session: SessionDep,
    user: AdminDep,
    action: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[AuditEntryOut]:
    """The company's audit trail, newest first (admin)."""
    entries = await AuditService(session).list_entries(user.company_id, action=action, limit=limit)
    return [AuditEntryOut.from_model(e) for e in entries]
