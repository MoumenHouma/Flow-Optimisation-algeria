"""Public REST API (F10) — key-authed endpoints for e-commerce integration.

Mounted under ``/api/public/v1``. Authentication is by API key (``X-API-Key``),
not a user session, so partners integrate without a login. Scopes gate access:
reading delivery status needs ``read``; creating deliveries needs ``write``.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core import audit
from routeopt.core.api_auth import ApiClient, require_scope
from routeopt.core.audit import client_ip
from routeopt.core.exceptions import NotFoundError
from routeopt.database import get_session
from routeopt.models.delivery import Delivery
from routeopt.modules.orders.schemas import DeliveryIn
from routeopt.modules.orders.service import OrdersService
from routeopt.modules.public_api.schemas import PublicDeliveryIn, PublicDeliveryOut

router = APIRouter(prefix="/public/v1", tags=["public-api"])
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.post("/deliveries", response_model=PublicDeliveryOut, status_code=201)
async def create_delivery(
    payload: PublicDeliveryIn,
    session: SessionDep,
    client: Annotated[ApiClient, Depends(require_scope("write"))],
    request: Request,
) -> PublicDeliveryOut:
    """Create a delivery (geocoded if no coordinates are supplied)."""
    item = DeliveryIn(
        order_id=payload.order_id,
        address=payload.address,
        address_locale=payload.address_locale,
        lat=payload.lat,
        lon=payload.lon,
        customer_phone=payload.customer_phone,
        time_window_start=payload.time_window_start,
        time_window_end=payload.time_window_end,
        weight=payload.weight,
        priority=payload.priority,
    )
    (delivery,) = await OrdersService(session).bulk_create(client.company_id, [item])
    await audit.record(
        session,
        action="public_api.delivery_created",
        resource_type="delivery",
        company_id=client.company_id,
        resource_id=delivery.id,
        metadata={"api_key_id": client.key_id, "order_id": payload.order_id},
        ip_address=client_ip(request),
    )
    await session.commit()
    return PublicDeliveryOut.from_model(delivery)


@router.get("/deliveries/{delivery_id}", response_model=PublicDeliveryOut)
async def get_delivery(
    delivery_id: str,
    session: SessionDep,
    client: Annotated[ApiClient, Depends(require_scope("read"))],
) -> PublicDeliveryOut:
    """Track a single delivery's status."""
    delivery = await session.get(Delivery, uuid.UUID(delivery_id))
    if delivery is None or str(delivery.company_id) != client.company_id or delivery.deleted_at:
        raise NotFoundError("Delivery not found")
    return PublicDeliveryOut.from_model(delivery)


@router.get("/deliveries", response_model=list[PublicDeliveryOut])
async def list_deliveries(
    session: SessionDep,
    client: Annotated[ApiClient, Depends(require_scope("read"))],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[PublicDeliveryOut]:
    """List the most recent deliveries for the authenticated company."""
    rows = await session.scalars(
        select(Delivery)
        .where(
            Delivery.company_id == uuid.UUID(client.company_id),
            Delivery.deleted_at.is_(None),
        )
        .order_by(Delivery.created_at.desc())
        .limit(limit)
    )
    return [PublicDeliveryOut.from_model(d) for d in rows]
