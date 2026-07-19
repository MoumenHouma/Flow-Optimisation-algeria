"""Route endpoints — docs/ARCHITECTURE.md §2.2 (Route Service)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.dependencies import CurrentUser, get_current_user, rate_limiter, require_roles
from routeopt.database import get_session
from routeopt.modules.routes.schemas import (
    JobOut,
    OptimizeRequest,
    OptimizeResponse,
    RouteOut,
    RouteStopOut,
)
from routeopt.modules.routes.service import RoutesService
from routeopt.schemas.common import JobStatus

router = APIRouter(prefix="/routes", tags=["routes"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("/optimize", response_model=OptimizeResponse, status_code=202)
async def optimize(
    payload: OptimizeRequest,
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "manager"))],
    _: Annotated[None, Depends(rate_limiter)],
) -> OptimizeResponse:
    """Submit an optimization job (F3). Returns a job id immediately; poll /jobs/{id}."""
    job_id, delivery_count = await RoutesService(session).submit_job(
        user.company_id, user.user_id, payload
    )
    return OptimizeResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        estimated_duration_ms=RoutesService.estimate_duration_ms(delivery_count),
    )


@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(
    job_id: str,
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> JobOut:
    service = RoutesService(session)
    job = await service.get_job(user.company_id, job_id)
    route_ids = await service.route_ids_for_job(job_id) if job.status == "completed" else []
    return JobOut(
        job_id=str(job.id),
        status=JobStatus(job.status),
        delivery_count=job.delivery_count,
        vehicle_count=job.vehicle_count,
        solver_strategy=job.solver_strategy,
        duration_ms=job.duration_ms,
        total_distance_m=(job.result or {}).get("total_distance_m") if job.result else None,
        route_ids=route_ids,
        error_message=job.error_message,
    )


@router.get("/{route_id}", response_model=RouteOut)
async def get_route(
    route_id: str,
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> RouteOut:
    route = await RoutesService(session).get_route(user.company_id, route_id)
    return RouteOut(
        id=str(route.id),
        vehicle_id=str(route.vehicle_id) if route.vehicle_id else None,
        total_distance_m=(
            float(route.total_distance_m) if route.total_distance_m is not None else None
        ),
        total_time_s=route.total_time_s,
        status=route.status,
        stops=[
            RouteStopOut(
                delivery_id=str(s.delivery_id),
                sequence=s.sequence,
                eta=s.eta.isoformat() if s.eta else None,
            )
            for s in route.stops
        ],
    )
