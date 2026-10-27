"""Schemas for the COD reconciliation API (F17)."""

from typing import Any, Literal

from pydantic import BaseModel


class CodPaymentOut(BaseModel):
    id: str
    delivery_id: str
    order_id: str | None
    route_id: str | None
    driver_user_id: str | None
    amount_expected: float | None
    amount_collected: float
    currency: str
    method: str
    status: str
    collected_at: str | None

    @classmethod
    def from_model(cls, c: Any, order_id: str | None = None) -> "CodPaymentOut":
        return cls(
            id=str(c.id),
            delivery_id=str(c.delivery_id),
            order_id=order_id,
            route_id=str(c.route_id) if c.route_id is not None else None,
            driver_user_id=str(c.driver_user_id) if c.driver_user_id is not None else None,
            amount_expected=(float(c.amount_expected) if c.amount_expected is not None else None),
            amount_collected=float(c.amount_collected),
            currency=c.currency,
            method=c.method,
            status=c.status,
            collected_at=c.collected_at.isoformat() if c.collected_at is not None else None,
        )


class CodSummaryRow(BaseModel):
    """One driver × day reconciliation bucket."""

    driver_user_id: str | None
    day: str  # ISO date
    count: int
    total_expected: float
    total_collected: float
    discrepancies: int


class CodSummaryOut(BaseModel):
    rows: list[CodSummaryRow]
    total_expected: float
    total_collected: float
    discrepancies: int


class ReconcileIn(BaseModel):
    # 'reconciled' = manager confirms the cash was handed in and matches;
    # 'discrepancy' = flagged for follow-up.
    status: Literal["reconciled", "discrepancy"]
