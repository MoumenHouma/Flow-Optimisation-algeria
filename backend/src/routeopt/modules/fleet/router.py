"""Fleet endpoints — docs/ARCHITECTURE.md §2.2 (Fleet Service)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from routeopt.core.dependencies import CurrentUser, get_current_user, require_roles
from routeopt.modules.fleet.schemas import VehicleIn, VehicleOut
from routeopt.modules.fleet.service import FleetService

router = APIRouter(prefix="/fleet", tags=["fleet"])
service = FleetService()


@router.get("/vehicles", response_model=list[VehicleOut])
async def list_vehicles(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[VehicleOut]:
    raise NotImplementedError("service.list_vehicles(user.company_id)")


@router.post("/vehicles", response_model=VehicleOut, status_code=201)
async def add_vehicle(
    payload: VehicleIn,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "manager"))],
) -> VehicleOut:
    raise NotImplementedError("service.add_vehicle(user.company_id, payload)")


@router.put("/vehicles/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(
    vehicle_id: str,
    payload: VehicleIn,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "manager"))],
) -> VehicleOut:
    raise NotImplementedError("service.update_vehicle(user.company_id, vehicle_id, payload)")
