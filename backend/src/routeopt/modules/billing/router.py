"""Billing endpoints (F19) — plan state, usage, plan changes, invoices.

Reading billing/usage is open to any authenticated user in the tenant; changing
plan and recording payments are admin-only (they move money and lift quotas).
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.dependencies import CurrentUser, get_current_user, require_roles
from routeopt.database import get_session
from routeopt.modules.billing.schemas import (
    BillingOut,
    ChangePlanIn,
    InvoiceOut,
    RecordPaymentIn,
)
from routeopt.modules.billing.service import BillingService

router = APIRouter(prefix="/billing", tags=["billing"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
AdminDep = Annotated[CurrentUser, Depends(require_roles("admin"))]


@router.get("", response_model=BillingOut)
async def get_billing(
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> BillingOut:
    """Current plan, price and usage-vs-quota for the caller's company."""
    return await BillingService(session).get_billing(user.company_id)


@router.get("/invoices", response_model=list[InvoiceOut])
async def list_invoices(
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[InvoiceOut]:
    """Billing history, newest period first."""
    return await BillingService(session).list_invoices(user.company_id)


@router.put("/plan", response_model=BillingOut)
async def change_plan(payload: ChangePlanIn, session: SessionDep, user: AdminDep) -> BillingOut:
    """Change the company plan (admin). Applies the tier's caps immediately."""
    return await BillingService(session).change_plan(user.company_id, payload)


@router.post("/invoices/pay", response_model=InvoiceOut, status_code=201)
async def record_payment(
    payload: RecordPaymentIn, session: SessionDep, user: AdminDep
) -> InvoiceOut:
    """Record an offline payment for a period, issuing/settling its invoice (admin)."""
    return await BillingService(session).record_payment(user.company_id, payload)
