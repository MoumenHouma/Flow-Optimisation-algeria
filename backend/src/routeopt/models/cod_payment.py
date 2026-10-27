"""CodPayment — cash collected for one cash-on-delivery stop (F17).

One row per delivery once the driver reports collection in the field. The
``amount_expected`` is copied from ``deliveries.cod_amount`` at collection time
so the reconciliation record is a stable snapshot even if the order total is
later edited. A mismatch between expected and collected flips ``status`` to
``discrepancy`` for the manager to resolve. PRD §4.1 "paiement à la livraison".
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


class CodPayment(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "cod_payments"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False
    )
    route_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.id", ondelete="SET NULL")
    )
    driver_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    amount_expected: Mapped[float | None] = mapped_column(Numeric(12, 2))
    amount_collected: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="DZD")
    method: Mapped[str] = mapped_column(String(20), nullable=False, default="cash")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="collected")
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        # One reconciliation record per delivery — re-report overwrites in place.
        UniqueConstraint("delivery_id", name="uq_cod_delivery"),
        CheckConstraint("method IN ('cash','baridimob','ccp','none')", name="check_cod_method"),
        CheckConstraint(
            "status IN ('pending','collected','reconciled','discrepancy')",
            name="check_cod_status",
        ),
        CheckConstraint("amount_collected >= 0", name="check_cod_collected"),
        CheckConstraint(
            "amount_expected IS NULL OR amount_expected >= 0", name="check_cod_expected"
        ),
    )
