"""FuelStation — a refuel point with live availability (F20).

Tracks which stations are usable right now so dispatchers can react to Algeria's
fuel shortages (PRD §4.1): ``available`` / ``shortage`` (queues, rationed) /
``closed``. Company-scoped — each fleet curates the stations it relies on.
"""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from routeopt.models.base import Base, SoftDelete, Timestamps, UUIDPrimaryKey


class FuelStation(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    __tablename__ = "fuel_stations"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    lat: Mapped[float] = mapped_column(Numeric(10, 8), nullable=False)
    lon: Mapped[float] = mapped_column(Numeric(11, 8), nullable=False)
    # Which fuels this station serves, comma-separated (essence,diesel,gpl,electric).
    fuel_types: Mapped[str] = mapped_column(String(100), nullable=False, default="essence")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="available")
    notes: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("status IN ('available','shortage','closed')", name="check_station_status"),
        CheckConstraint("lat BETWEEN -90 AND 90", name="check_station_lat"),
        CheckConstraint("lon BETWEEN -180 AND 180", name="check_station_lon"),
    )
