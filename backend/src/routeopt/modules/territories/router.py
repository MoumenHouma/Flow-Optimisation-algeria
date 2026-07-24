"""Territory endpoints (F15) — zones + auto-clustering (manager/admin)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core import audit
from routeopt.core.audit import client_ip
from routeopt.core.dependencies import CurrentUser, get_current_user, require_roles
from routeopt.database import get_session
from routeopt.modules.territories.schemas import (
    AutoGenerateRequest,
    TerritoryIn,
    TerritoryOut,
    TerritoryUpdate,
)
from routeopt.modules.territories.service import TerritoryService

router = APIRouter(prefix="/territories", tags=["territories"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]
ManagerDep = Annotated[CurrentUser, Depends(require_roles("admin", "manager"))]


@router.get("", response_model=list[TerritoryOut])
async def list_territories(
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[TerritoryOut]:
    rows = await TerritoryService(session).list_territories(user.company_id)
    return [TerritoryOut.from_model(t, n) for t, n in rows]


@router.post("", response_model=TerritoryOut, status_code=201)
async def create_territory(
    payload: TerritoryIn, session: SessionDep, user: ManagerDep
) -> TerritoryOut:
    territory = await TerritoryService(session).create_territory(user.company_id, payload)
    return TerritoryOut.from_model(territory)


@router.post("/auto-generate", response_model=list[TerritoryOut], status_code=201)
async def auto_generate(
    payload: AutoGenerateRequest, session: SessionDep, user: ManagerDep
) -> list[TerritoryOut]:
    """Cluster geocoded deliveries into zones and assign drivers round-robin."""
    rows = await TerritoryService(session).auto_generate(user.company_id, payload.zones)
    return [TerritoryOut.from_model(t, n) for t, n in rows]


@router.put("/{territory_id}", response_model=TerritoryOut)
async def update_territory(
    territory_id: str,
    payload: TerritoryUpdate,
    session: SessionDep,
    user: ManagerDep,
    request: Request,
) -> TerritoryOut:
    territory = await TerritoryService(session).update_territory(
        user.company_id, territory_id, payload
    )
    # Driver (re)assignment is a sensitive change — audit it (H2).
    if "driver_user_id" in payload.model_fields_set:
        await audit.record(
            session,
            action="territory.driver_assigned",
            resource_type="territory",
            company_id=user.company_id,
            actor_user_id=user.user_id,
            resource_id=territory_id,
            metadata={"driver_user_id": payload.driver_user_id},
            ip_address=client_ip(request),
        )
        await session.commit()
    return TerritoryOut.from_model(territory)


@router.delete("/{territory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_territory(territory_id: str, session: SessionDep, user: ManagerDep) -> Response:
    await TerritoryService(session).delete_territory(user.company_id, territory_id)
    return Response(status_code=204)
