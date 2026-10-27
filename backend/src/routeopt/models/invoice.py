"""Invoice — a billing charge for a company, one per period (F19).

Algerian SaaS payment is largely offline (CCP transfer, BaridiMob, cash), so an
invoice is created ``pending`` and marked ``paid`` when the manager confirms the
receipt; a Stripe path exists for card-capable Enterprise clients. Amounts in DZD
(PRD §5.1). ``period`` is the billed month as ``YYYY-MM``.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from routeopt.models.base import Base, Timestamps, UUIDPrimaryKey


class Invoice(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "invoices"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="SET NULL")
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    plan: Mapped[str] = mapped_column(String(50), nullable=False)
    amount_da: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    method: Mapped[str | None] = mapped_column(String(20))
    reference: Mapped[str | None] = mapped_column(String(255))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("company_id", "period", name="uq_invoice_company_period"),
        CheckConstraint("status IN ('pending','paid','void')", name="check_invoice_status"),
        CheckConstraint(
            "method IS NULL OR method IN ('cash','ccp','baridimob','stripe')",
            name="check_invoice_method",
        ),
        CheckConstraint("amount_da >= 0", name="check_invoice_amount"),
    )
