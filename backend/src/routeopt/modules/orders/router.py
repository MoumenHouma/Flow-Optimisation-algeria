"""Orders endpoints — docs/ARCHITECTURE.md §2.2 (Order Service)."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.dependencies import CurrentUser, get_current_user, require_roles
from routeopt.database import get_session
from routeopt.modules.orders.schemas import BulkCreateResponse, DeliveryIn, DeliveryOut
from routeopt.modules.orders.service import OrdersService

router = APIRouter(prefix="/orders", tags=["orders"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("", response_model=BulkCreateResponse, status_code=201)
async def create_deliveries(
    items: Annotated[list[DeliveryIn], Body(min_length=1, max_length=500)],
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(require_roles("admin", "manager"))],
) -> BulkCreateResponse:
    """Create deliveries in bulk (F1). Rows with lat/lon skip geocoding."""
    deliveries = await OrdersService(session).bulk_create(user.company_id, items)
    out = [DeliveryOut.from_model(d) for d in deliveries]
    return BulkCreateResponse(
        created=len(out),
        geocoding_pending=sum(1 for d in out if d.geocoding_status == "pending"),
        deliveries=out,
    )


@router.get("", response_model=list[DeliveryOut])
async def list_routable(
    session: SessionDep,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> list[DeliveryOut]:
    deliveries = await OrdersService(session).list_routable(user.company_id)
    return [DeliveryOut.from_model(d) for d in deliveries]
