"""Driver endpoints (F8) — the delivery-runtime API for the Driver PWA."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.dependencies import CurrentUser, get_current_user
from routeopt.database import get_session
from routeopt.modules.driver.schemas import DriverRouteOut, StatusUpdate
from routeopt.modules.driver.service import DriverService
from routeopt.modules.orders.schemas import DeliveryOut

router = APIRouter(prefix="/driver", tags=["driver"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/route", response_model=DriverRouteOut | None)
async def my_route(
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> DriverRouteOut | None:
    """The active route for the vehicle assigned to me (null if none today)."""
    return await DriverService(session).my_route(user.user_id)


@router.put("/deliveries/{delivery_id}/status", response_model=DeliveryOut)
async def update_delivery_status(
    delivery_id: str,
    payload: StatusUpdate,
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> DeliveryOut:
    """Mark a stop en_route / delivered / failed (records history + position)."""
    delivery = await DriverService(session).update_status(
        user.user_id, user.company_id, delivery_id, payload
    )
    return DeliveryOut.from_model(delivery)
