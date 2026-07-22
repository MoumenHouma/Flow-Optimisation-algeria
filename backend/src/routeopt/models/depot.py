"""Depot model — company warehouses / departure points (docs/SCHEMA.md §4.2, F12).

A depot is a shared departure point; vehicles reference one via
``vehicles.depot_id``. Vehicles keep their inline ``depot_lat/lon/address`` as the
resolved coordinates so the optimizer, driver app, and exports are unchanged.
"""

import uuid

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from routeopt.models.base import Base, SoftDelete, Timestamps, UUIDPrimaryKey


class Depot(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    __tablename__ = "depots"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    lat: Mapped[float] = mapped_column(Numeric(10, 8), nullable=False)
    lon: Mapped[float] = mapped_column(Numeric(11, 8), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint("lat BETWEEN -90 AND 90", name="check_depot_lat"),
        CheckConstraint("lon BETWEEN -180 AND 180", name="check_depot_lon"),
    )
