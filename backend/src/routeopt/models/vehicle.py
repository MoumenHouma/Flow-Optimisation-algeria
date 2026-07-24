"""Vehicle model — docs/SCHEMA.md §4.1. Supports mixed fleets (PRD §4.2)."""

import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from routeopt.models.base import Base, SoftDelete, Timestamps, UUIDPrimaryKey


class Vehicle(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    __tablename__ = "vehicles"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    driver_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    # F12 multi-dépôt: when set, the depot coords below are resolved from this
    # depot. Null keeps the classic single, vehicle-local departure point.
    depot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("depots.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(20), nullable=False, default="car")
    license_plate: Mapped[str | None] = mapped_column(String(20))
    capacity_weight: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=1000)
    capacity_volume: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=10)
    depot_lat: Mapped[float] = mapped_column(Numeric(10, 8), nullable=False)
    depot_lon: Mapped[float] = mapped_column(Numeric(11, 8), nullable=False)
    depot_address: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # F20 fuel-shortage: max distance the vehicle can cover on a tank (NULL =
    # unlimited/no constraint). `fuel_type` scopes which stations refuel it,
    # incl. Algeria's GPL/sirghaz. PRD §4.1 "pénurie carburant".
    fuel_range_km: Mapped[float | None] = mapped_column(Numeric(8, 2))
    fuel_type: Mapped[str] = mapped_column(String(20), nullable=False, default="essence")

    __table_args__ = (
        CheckConstraint(
            "vehicle_type IN ('car','van','truck','motorcycle')", name="check_vehicle_type"
        ),
        CheckConstraint(
            "fuel_type IN ('essence','diesel','gpl','electric')", name="check_fuel_type"
        ),
        CheckConstraint("capacity_weight >= 0", name="check_capacity_weight"),
        CheckConstraint("capacity_volume >= 0", name="check_capacity_volume"),
        CheckConstraint("fuel_range_km IS NULL OR fuel_range_km > 0", name="check_fuel_range"),
        CheckConstraint("depot_lat BETWEEN -90 AND 90", name="check_depot_lat"),
        CheckConstraint("depot_lon BETWEEN -180 AND 180", name="check_depot_lon"),
    )
