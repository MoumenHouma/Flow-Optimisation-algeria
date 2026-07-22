"""Delivery model — docs/SCHEMA.md §5.1.

Geocoding tolerance (matched/approximate/failed) reflects the imprecise-address
reality of the Algerian market (PRD §4.1, §4.3).

Note: the generated ``geog GEOGRAPHY(POINT,4326)`` column (SCHEMA.md §5.1, §8.2)
is a Postgres computed column managed directly in the Alembic migration, not
mapped here — keep the two in sync when changing the geo columns.
"""

import uuid
from datetime import time

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from routeopt.models.base import Base, SoftDelete, Timestamps, UUIDPrimaryKey


class Delivery(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    __tablename__ = "deliveries"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    route_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.id", ondelete="SET NULL")
    )
    # F15 multi-zone: the geographic territory this delivery belongs to.
    territory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("territories.id", ondelete="SET NULL")
    )
    order_id: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str] = mapped_column(Text, nullable=False)
    address_locale: Mapped[str] = mapped_column(String(10), nullable=False, default="fr")
    lat: Mapped[float | None] = mapped_column(Numeric(10, 8))
    lon: Mapped[float | None] = mapped_column(Numeric(11, 8))
    geocoding_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    customer_phone: Mapped[str | None] = mapped_column(String(30))
    time_window_start: Mapped[time | None] = mapped_column(Time)
    time_window_end: Mapped[time | None] = mapped_column(Time)
    service_time: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    weight: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    volume: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("priority IN (1,2,3)", name="check_priority"),
        CheckConstraint(
            "status IN ('pending','geocoded','assigned','en_route',"
            "'delivered','failed','cancelled')",
            name="check_status",
        ),
        CheckConstraint(
            "geocoding_status IN ('pending','matched','approximate','failed')",
            name="check_geocoding_status",
        ),
        CheckConstraint("lat IS NULL OR lat BETWEEN -90 AND 90", name="check_lat"),
        CheckConstraint("lon IS NULL OR lon BETWEEN -180 AND 180", name="check_lon"),
        CheckConstraint("weight >= 0", name="check_weight"),
        CheckConstraint("volume >= 0", name="check_volume"),
        CheckConstraint(
            "time_window_start IS NULL OR time_window_end IS NULL "
            "OR time_window_start <= time_window_end",
            name="check_time_window",
        ),
    )
