"""ServiceTimeModel — trained per-company service-time predictor (F13).

A lightweight cohort model: median observed service time per feature cohort
(geo-cell × hour × priority × weight × locale), stored as JSON. Trained offline
from ``delivery_status_history`` (en_route → delivered deltas); read at optimize
time to fill each delivery's ``service_time``. One row per company.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from routeopt.models.base import Base


class ServiceTimeModel(Base):
    __tablename__ = "service_time_models"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    # {"cohorts": {"<key>": median_s, ...}, "global_median_s": int}
    model: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cohort_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    global_median_s: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    mae_seconds: Mapped[float | None] = mapped_column(Numeric(10, 2))
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("company_id", name="uq_service_time_models_company"),)
