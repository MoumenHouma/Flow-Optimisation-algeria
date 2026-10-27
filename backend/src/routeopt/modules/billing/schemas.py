"""Billing DTOs (F19)."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class UsageOut(BaseModel):
    vehicles: int
    max_vehicles: int | None
    deliveries_today: int
    max_deliveries_per_day: int | None
    deliveries_this_month: int


class BillingOut(BaseModel):
    plan: str
    price_da: float
    status: str  # active subscription status, or "none"
    usage: UsageOut


class InvoiceOut(BaseModel):
    id: str
    period: str
    plan: str
    amount_da: float
    status: str
    method: str | None
    reference: str | None
    issued_at: str
    paid_at: str | None

    @classmethod
    def from_model(cls, i: Any) -> "InvoiceOut":
        return cls(
            id=str(i.id),
            period=i.period,
            plan=i.plan,
            amount_da=float(i.amount_da),
            status=i.status,
            method=i.method,
            reference=i.reference,
            issued_at=i.issued_at.isoformat(),
            paid_at=i.paid_at.isoformat() if i.paid_at is not None else None,
        )


class ChangePlanIn(BaseModel):
    plan: Literal["free", "starter", "pro", "enterprise"]


class RecordPaymentIn(BaseModel):
    # Confirm an offline payment for a billing period, issuing/settling its invoice.
    period: str = Field(..., pattern=r"^\d{4}-\d{2}$")  # YYYY-MM
    method: Literal["cash", "ccp", "baridimob", "stripe"] = "ccp"
    reference: str | None = None
    amount_da: float | None = Field(None, ge=0)  # defaults to the plan price
