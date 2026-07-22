"""Fleet endpoints — docs/ARCHITECTURE.md §2.2 (Fleet Service)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.dependencies import CurrentUser, get_current_user, require_roles
from routeopt.database import get_session
from routeopt.modules.fleet.schemas import (
    DepotIn,
    DepotOut,
    DriverIn,
    DriverOut,
    FleetSummary,
    VehicleIn,
    VehicleOut,
)
from routeopt.modules.fleet.service import FleetService

router = APIRouter(prefix="/fleet", tags=["fleet"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
ManagerDep = Annotated[CurrentUser, Depends(require_roles("admin", "manager"))]


@router.get("/summary", response_model=FleetSummary)
async def fleet_summary(
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> FleetSummary:
    return await FleetService(session).summary(user.company_id)


@router.get("/vehicles", response_model=list[VehicleOut])
async def list_vehicles(
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[VehicleOut]:
    vehicles = await FleetService(session).list_vehicles(user.company_id)
    return [VehicleOut.from_model(v) for v in vehicles]


@router.post("/vehicles", response_model=VehicleOut, status_code=201)
async def add_vehicle(payload: VehicleIn, session: SessionDep, user: ManagerDep) -> VehicleOut:
    vehicle = await FleetService(session).add_vehicle(user.company_id, payload)
    return VehicleOut.from_model(vehicle)


@router.post("/drivers", response_model=DriverOut, status_code=201)
async def create_driver(payload: DriverIn, session: SessionDep, user: ManagerDep) -> DriverOut:
    """Create a driver login (F8). Assign to a vehicle via its driver_user_id."""
    driver = await FleetService(session).create_driver(user.company_id, payload)
    return DriverOut.from_model(driver)


@router.put("/vehicles/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(
    vehicle_id: str, payload: VehicleIn, session: SessionDep, user: ManagerDep
) -> VehicleOut:
    vehicle = await FleetService(session).update_vehicle(user.company_id, vehicle_id, payload)
    return VehicleOut.from_model(vehicle)


@router.delete("/vehicles/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(vehicle_id: str, session: SessionDep, user: ManagerDep) -> None:
    await FleetService(session).delete_vehicle(user.company_id, vehicle_id)


# ── Depots (F12 multi-dépôt) ─────────────────────────────────────────────
@router.get("/depots", response_model=list[DepotOut])
async def list_depots(
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[DepotOut]:
    depots = await FleetService(session).list_depots(user.company_id)
    return [DepotOut.from_model(d) for d in depots]


@router.post("/depots", response_model=DepotOut, status_code=201)
async def add_depot(payload: DepotIn, session: SessionDep, user: ManagerDep) -> DepotOut:
    depot = await FleetService(session).add_depot(user.company_id, payload)
    return DepotOut.from_model(depot)


@router.put("/depots/{depot_id}", response_model=DepotOut)
async def update_depot(
    depot_id: str, payload: DepotIn, session: SessionDep, user: ManagerDep
) -> DepotOut:
    depot = await FleetService(session).update_depot(user.company_id, depot_id, payload)
    return DepotOut.from_model(depot)


@router.delete("/depots/{depot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_depot(depot_id: str, session: SessionDep, user: ManagerDep) -> None:
    await FleetService(session).delete_depot(user.company_id, depot_id)
