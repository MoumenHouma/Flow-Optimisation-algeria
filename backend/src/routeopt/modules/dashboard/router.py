"""Dashboard endpoints — docs/DESIGN.md §3.2 (F6)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.dependencies import CurrentUser, get_current_user
from routeopt.database import get_session
from routeopt.modules.dashboard.schemas import DashboardSummary
from routeopt.modules.dashboard.service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> DashboardSummary:
    return await DashboardService(session).summary(user.company_id)
