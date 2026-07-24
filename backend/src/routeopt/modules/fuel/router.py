"""Fuel-station endpoints (F20) — live availability for dispatchers.

Reading stations is open to any authenticated user in the tenant; creating,
updating status and deleting are manager/admin actions.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.dependencies import CurrentUser, get_current_user, require_roles
from routeopt.database import get_session
from routeopt.modules.fuel.schemas import FuelStationIn, FuelStationOut, FuelStatusIn
from routeopt.modules.fuel.service import FuelService

router = APIRouter(prefix="/fuel/stations", tags=["fuel"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
ManagerDep = Annotated[CurrentUser, Depends(require_roles("admin", "manager"))]


@router.get("", response_model=list[FuelStationOut])
async def list_stations(
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[FuelStationOut]:
    """Fuel stations for the company, ordered by name."""
    return await FuelService(session).list_stations(user.company_id)


@router.post("", response_model=FuelStationOut, status_code=201)
async def create_station(
    payload: FuelStationIn, session: SessionDep, user: ManagerDep
) -> FuelStationOut:
    """Add a fuel station (manager)."""
    return await FuelService(session).create_station(user.company_id, payload)


@router.put("/{station_id}/status", response_model=FuelStationOut)
async def set_status(
    station_id: str, payload: FuelStatusIn, session: SessionDep, user: ManagerDep
) -> FuelStationOut:
    """Update a station's availability (available / shortage / closed)."""
    return await FuelService(session).set_status(user.company_id, station_id, payload)


@router.delete("/{station_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_station(station_id: str, session: SessionDep, user: ManagerDep) -> None:
    """Soft-delete a fuel station (manager)."""
    await FuelService(session).delete_station(user.company_id, station_id)
