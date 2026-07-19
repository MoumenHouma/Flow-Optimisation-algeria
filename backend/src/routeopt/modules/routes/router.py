"""Route endpoints — docs/ARCHITECTURE.md §2.2 (Route Service)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from routeopt.core.dependencies import CurrentUser, get_current_user, rate_limiter, require_roles
from routeopt.modules.routes.schemas import OptimizeRequest, OptimizeResponse, RouteOut
from routeopt.modules.routes.service import RoutesService
from routeopt.schemas.common import JobStatus

router = APIRouter(prefix="/routes", tags=["routes"])
service = RoutesService()


@router.post("/optimize", response_model=OptimizeResponse, status_code=202)
async def optimize(
    payload: OptimizeRequest,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "manager"))],
    _: Annotated[None, Depends(rate_limiter)],
) -> OptimizeResponse:
    """Submit an optimization job (F3). Returns a job id immediately."""
    job_id = await service.submit_job(user.company_id, payload.model_dump())
    return OptimizeResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        estimated_duration_ms=service.estimate_duration_ms(len(payload.delivery_ids)),
    )


@router.get("/{route_id}", response_model=RouteOut)
async def get_route(
    route_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> RouteOut:
    raise NotImplementedError("service.get_route(user.company_id, route_id)")


@router.get("/{route_id}/export")
async def export_route(
    route_id: str,
    fmt: str = "pdf",
    user: Annotated[CurrentUser, Depends(get_current_user)] = ...,  # type: ignore[assignment]
) -> dict[str, str]:
    raise NotImplementedError("service.export(user.company_id, route_id, fmt)")


@router.post("/{route_id}/reoptimize", response_model=OptimizeResponse, status_code=202)
async def reoptimize(
    route_id: str,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "manager"))],
) -> OptimizeResponse:
    raise NotImplementedError("service.reoptimize(user.company_id, route_id)")
