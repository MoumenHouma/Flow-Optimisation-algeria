"""Orders logic: delivery creation + geocoding (F1, F2).

Deliveries with coordinates are stored ready-to-route (geocoding_status=matched).
Address-only deliveries are stored pending geocoding — the geocoder (Nominatim
with a 30d Redis cache, SCHEMA.md §7) is a follow-up; tolerating approximate
matches for imprecise Algerian addresses (PRD §4.1, §4.3).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.models.delivery import Delivery
from routeopt.modules.orders.schemas import DeliveryIn


class OrdersService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_create(self, company_id: str, items: list[DeliveryIn]) -> list[Delivery]:
        deliveries: list[Delivery] = []
        for item in items:
            has_coords = item.lat is not None and item.lon is not None
            delivery = Delivery(
                company_id=uuid.UUID(company_id),
                order_id=item.order_id,
                address=item.address,
                address_locale=item.address_locale,
                lat=item.lat,
                lon=item.lon,
                geocoding_status="matched" if has_coords else "pending",
                status="geocoded" if has_coords else "pending",
                customer_phone=item.customer_phone,
                time_window_start=item.time_window_start,
                time_window_end=item.time_window_end,
                service_time=item.service_time,
                weight=item.weight,
                volume=item.volume,
                priority=item.priority,
            )
            self.session.add(delivery)
            deliveries.append(delivery)
        await self.session.commit()
        for delivery in deliveries:
            await self.session.refresh(delivery)
        return deliveries

    async def list_routable(self, company_id: str) -> list[Delivery]:
        """Deliveries that can be optimized: geocoded, not yet on a route."""
        result = await self.session.scalars(
            select(Delivery).where(
                Delivery.company_id == uuid.UUID(company_id),
                Delivery.deleted_at.is_(None),
                Delivery.route_id.is_(None),
                Delivery.lat.is_not(None),
                Delivery.lon.is_not(None),
            )
        )
        return list(result)
