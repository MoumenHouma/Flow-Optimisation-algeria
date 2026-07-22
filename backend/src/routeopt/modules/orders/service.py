"""Orders logic: delivery creation + geocoding (F1, F2).

Deliveries supplied with coordinates are stored ready-to-route. Address-only
deliveries are geocoded via Nominatim (30d Redis cache, SCHEMA.md §7); a failed
lookup leaves the delivery ``pending`` so it can be corrected and retried
(DESIGN §3.5), while a street/area-level hit is accepted as ``approximate``
(imprecise Algerian addresses — PRD §4.1, §4.3).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.exceptions import NotFoundError
from routeopt.models.delivery import Delivery
from routeopt.modules.orders.geocoding import Geocoder
from routeopt.modules.orders.schemas import DeliveryIn
from routeopt.redis_client import redis_client


class OrdersService:
    def __init__(self, session: AsyncSession, geocoder: Geocoder | None = None) -> None:
        self.session = session
        self.geocoder = geocoder or Geocoder(redis_client)

    async def bulk_create(self, company_id: str, items: list[DeliveryIn]) -> list[Delivery]:
        deliveries: list[Delivery] = []
        for item in items:
            lat, lon, geocoding_status = await self._resolve_coords(item)
            delivery = Delivery(
                company_id=uuid.UUID(company_id),
                order_id=item.order_id,
                address=item.address,
                address_locale=item.address_locale,
                lat=lat,
                lon=lon,
                geocoding_status=geocoding_status,
                status="geocoded" if lat is not None else "pending",
                customer_phone=item.customer_phone,
                time_window_start=item.time_window_start,
                time_window_end=item.time_window_end,
                service_time=item.service_time,
                weight=item.weight,
                volume=item.volume,
                priority=item.priority,
                cod_amount=item.cod_amount,
                cod_currency=item.cod_currency,
            )
            self.session.add(delivery)
            deliveries.append(delivery)
        await self.session.commit()
        for delivery in deliveries:
            await self.session.refresh(delivery)
        return deliveries

    async def regeocode(self, company_id: str, delivery_id: str) -> Delivery:
        """Retry geocoding a delivery (correction flow, DESIGN §3.5)."""
        delivery = await self.session.get(Delivery, uuid.UUID(delivery_id))
        if delivery is None or str(delivery.company_id) != company_id:
            raise NotFoundError("Delivery not found")
        result = await self.geocoder.geocode(delivery.address)
        delivery.lat = result.lat
        delivery.lon = result.lon
        delivery.geocoding_status = result.status
        delivery.status = "geocoded" if result.lat is not None else "pending"
        await self.session.commit()
        await self.session.refresh(delivery)
        return delivery

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

    async def _resolve_coords(self, item: DeliveryIn) -> tuple[float | None, float | None, str]:
        if item.lat is not None and item.lon is not None:
            return item.lat, item.lon, "matched"
        result = await self.geocoder.geocode(item.address)
        return result.lat, result.lon, result.status
