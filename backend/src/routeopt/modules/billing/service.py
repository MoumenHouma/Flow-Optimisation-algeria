"""Billing logic (F19): plan state, usage metering, plan changes, invoices.

Changing a plan copies the plan's caps onto the company row so quota enforcement
(fleet / orders) reads authoritative limits from the DB and an upgrade lifts caps
immediately. Payment is recorded against a per-period invoice; the offline path
(CCP/BaridiMob/cash) is the default for the Algerian market. Read/write is always
tenant-scoped by ``company_id``.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.core.exceptions import NotFoundError, ValidationError
from routeopt.models.company import Company
from routeopt.models.delivery import Delivery
from routeopt.models.invoice import Invoice
from routeopt.models.subscription import Subscription
from routeopt.models.vehicle import Vehicle
from routeopt.modules.billing.plans import PLAN_SPECS
from routeopt.modules.billing.providers import ManualProvider, StripeProvider
from routeopt.modules.billing.schemas import (
    BillingOut,
    ChangePlanIn,
    InvoiceOut,
    RecordPaymentIn,
    UsageOut,
)


class BillingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _company(self, company_id: str) -> Company:
        company = await self.session.get(Company, uuid.UUID(company_id))
        if company is None or company.deleted_at is not None:
            raise NotFoundError("Company not found")
        return company

    async def _usage(self, company_id: str) -> UsageOut:
        cid = uuid.UUID(company_id)
        company = await self._company(company_id)
        now = datetime.now(UTC)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        vehicles = await self.session.scalar(
            select(func.count())
            .select_from(Vehicle)
            .where(Vehicle.company_id == cid, Vehicle.deleted_at.is_(None))
        )
        today = await self.session.scalar(
            select(func.count())
            .select_from(Delivery)
            .where(
                Delivery.company_id == cid,
                Delivery.deleted_at.is_(None),
                Delivery.created_at >= day_start,
            )
        )
        month = await self.session.scalar(
            select(func.count())
            .select_from(Delivery)
            .where(
                Delivery.company_id == cid,
                Delivery.deleted_at.is_(None),
                Delivery.created_at >= month_start,
            )
        )
        return UsageOut(
            vehicles=vehicles or 0,
            max_vehicles=company.max_vehicles,
            deliveries_today=today or 0,
            max_deliveries_per_day=company.max_deliveries_per_day,
            deliveries_this_month=month or 0,
        )

    async def _active_subscription(self, company_id: str) -> Subscription | None:
        return await self.session.scalar(
            select(Subscription).where(
                Subscription.company_id == uuid.UUID(company_id),
                Subscription.status == "active",
            )
        )

    async def get_billing(self, company_id: str) -> BillingOut:
        company = await self._company(company_id)
        sub = await self._active_subscription(company_id)
        spec = PLAN_SPECS[company.plan]
        return BillingOut(
            plan=company.plan,
            price_da=float(sub.amount_da) if sub is not None else spec.price_da,
            status=sub.status if sub is not None else "none",
            usage=await self._usage(company_id),
        )

    async def change_plan(self, company_id: str, payload: ChangePlanIn) -> BillingOut:
        company = await self._company(company_id)
        spec = PLAN_SPECS[payload.plan]

        # Apply the plan's caps to the company so quota checks read them from the DB.
        company.plan = payload.plan
        company.max_vehicles = spec.max_vehicles
        company.max_deliveries_per_day = spec.max_deliveries_per_day

        # Close the previous subscription and open one for the new plan.
        now = datetime.now(UTC)
        current = await self._active_subscription(company_id)
        if current is not None:
            current.status = "canceled"
            current.canceled_at = now
        self.session.add(
            Subscription(
                company_id=company.id,
                plan=payload.plan,
                status="active",
                amount_da=spec.price_da,
                started_at=now,
            )
        )
        await self.session.commit()
        return await self.get_billing(company_id)

    async def list_invoices(self, company_id: str) -> list[InvoiceOut]:
        rows = await self.session.scalars(
            select(Invoice)
            .where(Invoice.company_id == uuid.UUID(company_id))
            .order_by(Invoice.period.desc())
        )
        return [InvoiceOut.from_model(i) for i in rows]

    async def record_payment(self, company_id: str, payload: RecordPaymentIn) -> InvoiceOut:
        company = await self._company(company_id)
        sub = await self._active_subscription(company_id)
        amount = (
            payload.amount_da
            if payload.amount_da is not None
            else PLAN_SPECS[company.plan].price_da
        )

        provider = StripeProvider() if payload.method == "stripe" else ManualProvider()
        ref = provider.confirm(amount, payload.reference)
        now = datetime.now(UTC)

        invoice = await self.session.scalar(
            select(Invoice).where(
                Invoice.company_id == company.id, Invoice.period == payload.period
            )
        )
        if invoice is None:
            invoice = Invoice(
                company_id=company.id,
                period=payload.period,
                plan=company.plan,
                issued_at=now,
            )
            self.session.add(invoice)
        if invoice.status == "paid":
            raise ValidationError(f"Invoice for {payload.period} is already paid")
        invoice.subscription_id = sub.id if sub is not None else None
        invoice.plan = company.plan
        invoice.amount_da = amount
        invoice.method = payload.method
        invoice.reference = ref
        invoice.status = "paid"
        invoice.paid_at = now
        await self.session.commit()
        await self.session.refresh(invoice)
        return InvoiceOut.from_model(invoice)
