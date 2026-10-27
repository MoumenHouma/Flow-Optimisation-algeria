"""Driver runtime logic (F8): fetch my route, update delivery status + history."""

import contextlib
import uuid
from datetime import UTC, datetime, time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.config import get_settings
from routeopt.core.exceptions import NotFoundError, ValidationError
from routeopt.core.storage import Storage
from routeopt.core.webhooks import WebhookDispatcher
from routeopt.models.cod_payment import CodPayment
from routeopt.models.delivery import Delivery
from routeopt.models.delivery_status_history import DeliveryStatusHistory
from routeopt.models.proof_of_delivery import ProofOfDelivery
from routeopt.models.route import Route
from routeopt.models.vehicle import Vehicle
from routeopt.modules.driver.schemas import (
    DriverRouteOut,
    DriverStopOut,
    ProofOut,
    StatusUpdate,
)
from routeopt.modules.notifications.service import build_message, enqueue
from routeopt.modules.tracking.service import write_position
from routeopt.modules.tracking.tokens import make_token
from routeopt.redis_client import redis_client

_settings = get_settings()

_ACTIVE_ROUTE_STATUSES = ("planned", "dispatched", "in_progress")


def _hm(t: time | None) -> str | None:
    return t.strftime("%H:%M") if t is not None else None


class DriverService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def my_route(self, user_id: str, company_id: str) -> DriverRouteOut | None:
        """The current active route for the vehicle assigned to this driver."""
        vehicle = await self.session.scalar(
            select(Vehicle).where(
                Vehicle.driver_user_id == uuid.UUID(user_id),
                Vehicle.company_id == uuid.UUID(company_id),  # tenant isolation (M2)
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
                    cod_amount=(float(d.cod_amount) if d and d.cod_amount is not None else None),
                    cod_currency=d.cod_currency if d else "DZD",
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

    async def _authorize_delivery(
        self, user_id: str, company_id: str, delivery_id: str
    ) -> tuple[Delivery, Route]:
        """Fetch a delivery the calling driver owns, or raise (404 = no leak)."""
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
        # Only the driver assigned to the route's vehicle may touch it.
        if route is None or vehicle is None or str(vehicle.driver_user_id) != user_id:
            raise NotFoundError("Delivery not found")
        return delivery, route

    async def update_status(
        self, user_id: str, company_id: str, delivery_id: str, payload: StatusUpdate
    ) -> Delivery:
        delivery, route = await self._authorize_delivery(user_id, company_id, delivery_id)

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
        if route.status in ("planned", "dispatched"):
            route.status = "in_progress"

        # F17: on delivery, record the cash collected for a COD stop.
        cod = await self._record_cod(delivery, route, user_id, payload)

        await self.session.commit()
        await self.session.refresh(delivery)

        # Notify partner integrations (F10). Best-effort; never blocks the update.
        dispatcher = WebhookDispatcher(self.session)
        await dispatcher.dispatch(
            company_id,
            "delivery.status_changed",
            {
                "delivery_id": str(delivery.id),
                "order_id": delivery.order_id,
                "status": delivery.status,
                "reason": payload.reason,
            },
        )
        if cod is not None:
            await dispatcher.dispatch(
                company_id,
                "cod.collected",
                {
                    "delivery_id": str(delivery.id),
                    "order_id": delivery.order_id,
                    "amount_expected": (
                        float(cod.amount_expected) if cod.amount_expected is not None else None
                    ),
                    "amount_collected": float(cod.amount_collected),
                    "currency": cod.currency,
                    "method": cod.method,
                    "status": cod.status,
                },
            )

        # F18: notify the customer on status changes (enqueue only — never blocks).
        await self._notify_customer(delivery)
        return delivery

    async def _notify_customer(self, delivery: Delivery) -> None:
        """Queue a customer SMS/WhatsApp for a status change (best-effort)."""
        if not delivery.customer_phone:
            return
        tracking_url = f"{_settings.public_base_url}/track/{make_token(str(delivery.id))}"
        body = build_message(status=delivery.status, tracking_url=tracking_url)
        if body is None:
            return
        # Notifications never block a delivery update.
        with contextlib.suppress(Exception):
            await enqueue(redis_client, to=delivery.customer_phone, body=body, kind=delivery.status)

    async def record_location(self, user_id: str, company_id: str, lat: float, lon: float) -> None:
        """Store the calling driver's live vehicle position (F18 live tracking)."""
        vehicle = await self.session.scalar(
            select(Vehicle).where(
                Vehicle.driver_user_id == uuid.UUID(user_id),
                Vehicle.deleted_at.is_(None),
            )
        )
        if vehicle is None:
            raise NotFoundError("No vehicle assigned to this driver")
        await write_position(redis_client, company_id, str(vehicle.id), lat, lon)

    async def _record_cod(
        self, delivery: Delivery, route: Route, user_id: str, payload: StatusUpdate
    ) -> CodPayment | None:
        """Upsert the COD reconciliation row for a delivered stop that owes cash.

        Returns the row when one is written (so the caller can fire the webhook),
        else None. A collected amount short of / over the expected flips the row
        to ``discrepancy`` for the manager to resolve. Re-reporting overwrites the
        existing row in place (one record per delivery, uq_cod_delivery).
        """
        if payload.status != "delivered" or payload.cod_collected is None:
            return None
        if delivery.cod_amount is None and payload.cod_collected == 0:
            return None  # prepaid stop, nothing to reconcile

        expected = delivery.cod_amount
        collected = payload.cod_collected
        status = "collected"
        if expected is not None and Decimal(str(collected)) != Decimal(str(expected)):
            status = "discrepancy"

        cod = await self.session.scalar(
            select(CodPayment).where(CodPayment.delivery_id == delivery.id)
        )
        if cod is None:
            cod = CodPayment(company_id=delivery.company_id, delivery_id=delivery.id)
            self.session.add(cod)
        cod.route_id = route.id
        cod.driver_user_id = uuid.UUID(user_id)
        cod.amount_expected = expected
        cod.amount_collected = collected
        cod.currency = delivery.cod_currency
        cod.method = payload.cod_method
        cod.status = status
        cod.collected_at = datetime.now(UTC)
        return cod

    async def save_proof(
        self,
        user_id: str,
        company_id: str,
        delivery_id: str,
        photo: tuple[bytes, str] | None,
        signature: tuple[bytes, str] | None,
        lat: float | None,
        lon: float | None,
        storage: Storage,
    ) -> ProofOut:
        """Store a delivery's proof (photo/signature) — one per delivery, upsert."""
        delivery, _ = await self._authorize_delivery(user_id, company_id, delivery_id)
        if photo is None and signature is None:
            raise ValidationError("A photo or signature is required")

        proof = await self.session.scalar(
            select(ProofOfDelivery).where(ProofOfDelivery.delivery_id == delivery.id)
        )
        if proof is None:
            proof = ProofOfDelivery(delivery_id=delivery.id)
            self.session.add(proof)
        proof.driver_user_id = uuid.UUID(user_id)
        proof.lat = lat
        proof.lon = lon

        if photo is not None:
            data, content_type = photo
            key = f"pod/{delivery.id}/photo-{uuid.uuid4().hex}{_ext(content_type)}"
            await storage.put(key, data, content_type)
            proof.photo_url = key
        if signature is not None:
            data, content_type = signature
            key = f"pod/{delivery.id}/signature-{uuid.uuid4().hex}{_ext(content_type)}"
            await storage.put(key, data, content_type)
            proof.signature_url = key

        await self.session.commit()
        await self.session.refresh(proof)
        return await self._to_out(proof, storage)

    async def get_proof(
        self, user_id: str, company_id: str, delivery_id: str, storage: Storage
    ) -> ProofOut | None:
        delivery, _ = await self._authorize_delivery(user_id, company_id, delivery_id)
        proof = await self.session.scalar(
            select(ProofOfDelivery).where(ProofOfDelivery.delivery_id == delivery.id)
        )
        if proof is None:
            return None
        return await self._to_out(proof, storage)

    async def _to_out(self, proof: ProofOfDelivery, storage: Storage) -> ProofOut:
        return ProofOut(
            delivery_id=str(proof.delivery_id),
            photo_url=(await storage.presigned_get(proof.photo_url) if proof.photo_url else None),
            signature_url=(
                await storage.presigned_get(proof.signature_url) if proof.signature_url else None
            ),
            lat=float(proof.lat) if proof.lat is not None else None,
            lon=float(proof.lon) if proof.lon is not None else None,
            captured_at=proof.captured_at.isoformat(),
        )


_EXT_BY_TYPE = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


def _ext(content_type: str) -> str:
    return _EXT_BY_TYPE.get(content_type.lower().split(";")[0].strip(), "")
