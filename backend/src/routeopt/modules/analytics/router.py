"""Analytics endpoints (F11) — historical KPIs, trends, performance."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.dependencies import CurrentUser, require_roles
from routeopt.database import get_session
from routeopt.modules.analytics.schemas import PerformanceOut, TrendsOut
from routeopt.modules.analytics.service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
# Analytics is a management view (starter+ feature); managers/admins only.
ManagerDep = Annotated[CurrentUser, Depends(require_roles("admin", "manager"))]


@router.get("/trends", response_model=TrendsOut)
async def trends(
    session: SessionDep,
    user: ManagerDep,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> TrendsOut:
    """Daily delivered/failed counts, routes and distance over the window."""
    return await AnalyticsService(session).trends(user.company_id, days)


@router.get("/performance", response_model=PerformanceOut)
async def performance(
    session: SessionDep,
    user: ManagerDep,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> PerformanceOut:
    """Success rate, failure-reason breakdown and per-driver leaderboard."""
    return await AnalyticsService(session).performance(user.company_id, days)
