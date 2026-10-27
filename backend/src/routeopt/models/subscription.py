"""Subscription — a company's current paid plan (F19).

One active row per company reflecting the plan it is billed on. Changing plan
cancels the previous row (``status='canceled'``) and opens a new one, so the
table doubles as a plan-history audit. Prices are in Algerian dinar (DZD) per
PRD §5.1. Payment itself is recorded as Invoices.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from routeopt.models.base import Base, Timestamps, UUIDPrimaryKey


class Subscription(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "subscriptions"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    plan: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    amount_da: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("plan IN ('free','starter','pro','enterprise')", name="check_sub_plan"),
        CheckConstraint("status IN ('active','canceled')", name="check_sub_status"),
        CheckConstraint("amount_da >= 0", name="check_sub_amount"),
    )
