"""COD reconciliation logic (F17) — manager-side.

Lists cash-on-delivery records, aggregates them into a driver × day view for the
manager to reconcile against physical cash handed in, and lets the manager mark a
record reconciled or flag a discrepancy. Read/write is always tenant-scoped by
``company_id``.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.exceptions import NotFoundError
from routeopt.models.cod_payment import CodPayment
from routeopt.models.delivery import Delivery
from routeopt.modules.cod.schemas import (
    CodPaymentOut,
    CodSummaryOut,
    CodSummaryRow,
    ReconcileIn,
)


class CodService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _base_query(
        self,
        company_id: str,
        route_id: str | None,
        driver_id: str | None,
        date_from: date | None,
        date_to: date | None,
    ):
        query = select(CodPayment).where(CodPayment.company_id == uuid.UUID(company_id))
        if route_id is not None:
            query = query.where(CodPayment.route_id == uuid.UUID(route_id))
        if driver_id is not None:
            query = query.where(CodPayment.driver_user_id == uuid.UUID(driver_id))
        if date_from is not None:
            query = query.where(
                CodPayment.collected_at >= datetime.combine(date_from, datetime.min.time())
            )
        if date_to is not None:
            query = query.where(
                CodPayment.collected_at < datetime.combine(date_to, datetime.max.time())
            )
        return query

    async def list_payments(
        self,
        company_id: str,
        route_id: str | None = None,
        driver_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[CodPaymentOut]:
        query = self._base_query(company_id, route_id, driver_id, date_from, date_to).order_by(
            CodPayment.collected_at.desc()
        )
        rows = list(await self.session.scalars(query))
        # Fetch order_ids for display in one round-trip.
        order_ids: dict[uuid.UUID, str | None] = {}
        if rows:
            dids = [r.delivery_id for r in rows]
            for d in await self.session.scalars(select(Delivery).where(Delivery.id.in_(dids))):
                order_ids[d.id] = d.order_id
        return [CodPaymentOut.from_model(r, order_ids.get(r.delivery_id)) for r in rows]

    async def summary(
        self,
        company_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> CodSummaryOut:
        rows = list(
            await self.session.scalars(self._base_query(company_id, None, None, date_from, date_to))
        )
        buckets: dict[tuple[str | None, str], CodSummaryRow] = {}
        totals = {"expected": 0.0, "collected": 0.0, "disc": 0}
        for r in rows:
            driver = str(r.driver_user_id) if r.driver_user_id is not None else None
            day = (r.collected_at or r.created_at).date().isoformat()
            key = (driver, day)
            bucket = buckets.get(key)
            if bucket is None:
                bucket = CodSummaryRow(
                    driver_user_id=driver,
                    day=day,
                    count=0,
                    total_expected=0.0,
                    total_collected=0.0,
                    discrepancies=0,
                )
                buckets[key] = bucket
            bucket.count += 1
            expected = float(r.amount_expected) if r.amount_expected is not None else 0.0
            collected = float(r.amount_collected)
            bucket.total_expected += expected
            bucket.total_collected += collected
            totals["expected"] += expected
            totals["collected"] += collected
            if r.status == "discrepancy":
                bucket.discrepancies += 1
                totals["disc"] += 1
        ordered = sorted(
            buckets.values(), key=lambda b: (b.day, b.driver_user_id or ""), reverse=True
        )
        return CodSummaryOut(
            rows=ordered,
            total_expected=round(totals["expected"], 2),
            total_collected=round(totals["collected"], 2),
            discrepancies=totals["disc"],
        )

    async def set_status(
        self, company_id: str, payment_id: str, payload: ReconcileIn
    ) -> CodPaymentOut:
        cod = await self.session.get(CodPayment, uuid.UUID(payment_id))
        if cod is None or str(cod.company_id) != company_id:
            raise NotFoundError("COD payment not found")
        cod.status = payload.status
        await self.session.commit()
        await self.session.refresh(cod)
        delivery = await self.session.get(Delivery, cod.delivery_id)
        return CodPaymentOut.from_model(cod, delivery.order_id if delivery else None)
