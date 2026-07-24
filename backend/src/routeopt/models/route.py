"""Route + normalized RouteStop models — docs/SCHEMA.md §6.1, §6.2.

RouteStop is normalized (not a JSONB blob) because stops mutate individually
during dynamic re-optimization (F9); geometry stays JSONB (display-only).
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from routeopt.models.base import Base, SoftDelete, Timestamps, UUIDPrimaryKey


class Route(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    __tablename__ = "routes"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id", ondelete="SET NULL")
    )
    optimization_job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("optimization_jobs.id", ondelete="SET NULL")
    )
    name: Mapped[str | None] = mapped_column(String(100))
    total_distance_m: Mapped[float | None] = mapped_column(Numeric(10, 2))
    total_time_s: Mapped[int | None] = mapped_column(Integer)
    geometry: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # GeoJSON LineString
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="planned")
    optimized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    stops: Mapped[list["RouteStop"]] = relationship(
        back_populates="route", cascade="all, delete-orphan", order_by="RouteStop.sequence"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('planned','dispatched','in_progress','completed','cancelled')",
            name="check_route_status",
        ),
    )


class RouteStop(UUIDPrimaryKey, Base):
    __tablename__ = "route_stops"

    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False
    )
    delivery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    eta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    distance_from_previous_m: Mapped[float | None] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=None, nullable=True
    )

    route: Mapped[Route] = relationship(back_populates="stops")

    __table_args__ = (
        UniqueConstraint("route_id", "sequence", name="uq_route_stops_sequence"),
        UniqueConstraint("route_id", "delivery_id", name="uq_route_stops_delivery"),
    )
