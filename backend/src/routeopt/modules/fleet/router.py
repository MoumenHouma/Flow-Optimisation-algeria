"""Fleet endpoints — docs/ARCHITECTURE.md §2.2 (Fleet Service)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.dependencies import CurrentUser, get_current_user, require_roles
from routeopt.database import get_session
from routeopt.modules.fleet.schemas import VehicleIn, VehicleOut
from routeopt.modules.fleet.service import FleetService

router = APIRouter(prefix="/fleet", tags=["fleet"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/vehicles", response_model=list[VehicleOut])
async def list_vehicles(
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[VehicleOut]:
    vehicles = await FleetService(session).list_vehicles(user.company_id)
    return [VehicleOut.from_model(v) for v in vehicles]


@router.post("/vehicles", response_model=VehicleOut, status_code=201)
async def add_vehicle(
    payload: VehicleIn,
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "manager"))],
) -> VehicleOut:
    vehicle = await FleetService(session).add_vehicle(user.company_id, payload)
    return VehicleOut.from_model(vehicle)
