"""Route endpoints — docs/ARCHITECTURE.md §2.2 (Route Service)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.dependencies import CurrentUser, get_current_user, rate_limiter, require_roles
from routeopt.database import get_session
from routeopt.modules.routes.export import build_excel, build_pdf
from routeopt.modules.routes.schemas import (
    JobOut,
    OptimizeRequest,
    OptimizeResponse,
    RouteOut,
    RouteStopOut,
)
from routeopt.modules.routes.service import RoutesService
from routeopt.schemas.common import GeoPoint, JobStatus

router = APIRouter(prefix="/routes", tags=["routes"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]

_EXPORT_MEDIA = {
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


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
    route, deliveries, depot = await RoutesService(session).get_route_detail(
        user.company_id, route_id
    )
    stops: list[RouteStopOut] = []
    for s in route.stops:
        d = deliveries.get(s.delivery_id)
        stops.append(
            RouteStopOut(
                delivery_id=str(s.delivery_id),
                sequence=s.sequence,
                eta=s.eta.isoformat() if s.eta else None,
                lat=float(d.lat) if d and d.lat is not None else None,
                lon=float(d.lon) if d and d.lon is not None else None,
                address=d.address if d else None,
            )
        )
    return RouteOut(
        id=str(route.id),
        vehicle_id=str(route.vehicle_id) if route.vehicle_id else None,
        total_distance_m=(
            float(route.total_distance_m) if route.total_distance_m is not None else None
        ),
        total_time_s=route.total_time_s,
        status=route.status,
        depot=GeoPoint(**depot) if depot else None,
        geometry=route.geometry,
        stops=stops,
    )


@router.get("/{route_id}/export")
async def export_route(
    route_id: str,
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    format: Annotated[str, Query(pattern="^(pdf|xlsx)$")] = "pdf",
) -> Response:
    """Export a route's stop sheet as PDF or Excel (F5)."""
    route, deliveries, _ = await RoutesService(session).get_route_detail(user.company_id, route_id)
    content = build_excel(route, deliveries) if format == "xlsx" else build_pdf(route, deliveries)
    filename = f"tournee-{str(route.id)[:8]}.{format}"
    return Response(
        content=content,
        media_type=_EXPORT_MEDIA[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
