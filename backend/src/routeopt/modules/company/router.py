"""Company endpoints (F16) — read company + edit white-label branding."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.dependencies import CurrentUser, get_current_user, require_roles
from routeopt.database import get_session
from routeopt.modules.company.schemas import Branding, CompanyOut
from routeopt.modules.company.service import CompanyService

router = APIRouter(prefix="/company", tags=["company"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=CompanyOut)
async def get_company(
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CompanyOut:
    """The caller's company, including white-label branding for the UI."""
    company = await CompanyService(session).get_company(user.company_id)
    return CompanyOut.from_model(company)


@router.put("/branding", response_model=CompanyOut)
async def update_branding(
    payload: Branding,
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(require_roles("admin"))],
) -> CompanyOut:
    """Set the company's brand name, primary colour and logo (admin)."""
    company = await CompanyService(session).update_branding(user.company_id, payload)
    return CompanyOut.from_model(company)
