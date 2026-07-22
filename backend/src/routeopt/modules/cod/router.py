"""COD reconciliation endpoints (F17) — manager view over cash-on-delivery.

Drivers record the cash they collect through the driver status-update endpoint
(``PUT /driver/deliveries/{id}/status`` carries ``cod_collected``). These
endpoints are the manager side: list, aggregate and reconcile those records.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.dependencies import CurrentUser, require_roles
from routeopt.database import get_session
from routeopt.modules.cod.schemas import CodPaymentOut, CodSummaryOut, ReconcileIn
from routeopt.modules.cod.service import CodService

router = APIRouter(prefix="/cod", tags=["cod"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
# Cash reconciliation is a management responsibility — managers/admins only.
ManagerDep = Annotated[CurrentUser, Depends(require_roles("admin", "manager"))]


@router.get("/payments", response_model=list[CodPaymentOut])
async def list_payments(
    session: SessionDep,
    user: ManagerDep,
    route_id: Annotated[str | None, Query()] = None,
    driver_id: Annotated[str | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> list[CodPaymentOut]:
    """COD records, newest first, filterable by route / driver / date range."""
    return await CodService(session).list_payments(
        user.company_id, route_id, driver_id, date_from, date_to
    )


@router.get("/summary", response_model=CodSummaryOut)
async def summary(
    session: SessionDep,
    user: ManagerDep,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> CodSummaryOut:
    """Driver × day totals (expected vs collected) with discrepancy counts."""
    return await CodService(session).summary(user.company_id, date_from, date_to)


@router.put("/payments/{payment_id}", response_model=CodPaymentOut)
async def reconcile(
    payment_id: str,
    payload: ReconcileIn,
    session: SessionDep,
    user: ManagerDep,
) -> CodPaymentOut:
    """Mark a COD record reconciled, or flag it as a discrepancy."""
    return await CodService(session).set_status(user.company_id, payment_id, payload)
