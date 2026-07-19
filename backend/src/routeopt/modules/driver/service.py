"""Driver runtime logic (F8): fetch my route, update delivery status + history."""

import uuid
from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.exceptions import NotFoundError, ValidationError
from routeopt.models.delivery import Delivery
from routeopt.models.delivery_status_history import DeliveryStatusHistory
from routeopt.models.route import Route
from routeopt.models.vehicle import Vehicle
from routeopt.modules.driver.schemas import DriverRouteOut, DriverStopOut, StatusUpdate

_ACTIVE_ROUTE_STATUSES = ("planned", "dispatched", "in_progress")


def _hm(t: time | None) -> str | None:
    return t.strftime("%H:%M") if t is not None else None


class DriverService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def my_route(self, user_id: str) -> DriverRouteOut | None:
        """The current active route for the vehicle assigned to this driver."""
        vehicle = await self.session.scalar(
            select(Vehicle).where(
                Vehicle.driver_user_id == uuid.UUID(user_id),
                Vehicle.deleted_at.is_(None),
            )
        )
        if vehicle is None:
            return None

        route = await self.session.scalar(
            select(Route)
            .where(
                Route.vehicle_id == vehicle.id,
                Route.deleted_at.is_(None),
                Route.status.in_(_ACTIVE_ROUTE_STATUSES),
            )
            .order_by(Route.created_at.desc())
        )
        if route is None:
            return None
        await self.session.refresh(route, attribute_names=["stops"])

        ids = [s.delivery_id for s in route.stops]
        deliveries: dict[uuid.UUID, Delivery] = {}
        if ids:
            rows = await self.session.scalars(select(Delivery).where(Delivery.id.in_(ids)))
            deliveries = {d.id: d for d in rows}

        stops: list[DriverStopOut] = []
        delivered = 0
        for s in sorted(route.stops, key=lambda x: x.sequence):
            d = deliveries.get(s.delivery_id)
            if d is not None and d.status == "delivered":
                delivered += 1
            stops.append(
                DriverStopOut(
                    delivery_id=str(s.delivery_id),
                    sequence=s.sequence,
                    address=d.address if d else "",
                    lat=float(d.lat) if d and d.lat is not None else None,
                    lon=float(d.lon) if d and d.lon is not None else None,
                    customer_phone=d.customer_phone if d else None,
                    time_window_start=_hm(d.time_window_start) if d else None,
                    time_window_end=_hm(d.time_window_end) if d else None,
                    status=d.status if d else "pending",
                )
            )

        return DriverRouteOut(
            route_id=str(route.id),
            vehicle_name=vehicle.name,
            total_distance_m=(
                float(route.total_distance_m) if route.total_distance_m is not None else None
            ),
            delivered=delivered,
            total=len(stops),
            stops=stops,
        )

    async def update_status(
        self, user_id: str, company_id: str, delivery_id: str, payload: StatusUpdate
    ) -> Delivery:
        delivery = await self.session.get(Delivery, uuid.UUID(delivery_id))
        if delivery is None or str(delivery.company_id) != company_id:
            raise NotFoundError("Delivery not found")
        if delivery.route_id is None:
            raise ValidationError("Delivery is not assigned to a route")

        route = await self.session.get(Route, delivery.route_id)
        vehicle = (
            await self.session.get(Vehicle, route.vehicle_id)
            if route and route.vehicle_id
            else None
        )
        # Only the driver assigned to the route's vehicle may update it (404 = no leak).
        if vehicle is None or str(vehicle.driver_user_id) != user_id:
            raise NotFoundError("Delivery not found")

        self.session.add(
            DeliveryStatusHistory(
                delivery_id=delivery.id,
                from_status=delivery.status,
                to_status=payload.status,
                reason=payload.reason,
                changed_by_user_id=uuid.UUID(user_id),
                lat=payload.lat,
                lon=payload.lon,
            )
        )
        delivery.status = payload.status
        if route is not None and route.status in ("planned", "dispatched"):
            route.status = "in_progress"

        await self.session.commit()
        await self.session.refresh(delivery)
        return delivery
