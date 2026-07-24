"""Territory model — geographic delivery zones (F15, docs/PRD.md §3.3).

A territory groups nearby deliveries into a zone (auto-clustered from
``deliveries.geog`` coordinates) and can be assigned to a driver. Deliveries
reference their zone via ``deliveries.territory_id``.
"""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from routeopt.models.base import Base, SoftDelete, Timestamps, UUIDPrimaryKey


class Territory(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    __tablename__ = "territories"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(9), nullable=False, default="#2563EB")
    driver_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    centroid_lat: Mapped[float | None] = mapped_column(Numeric(10, 8))
    centroid_lon: Mapped[float | None] = mapped_column(Numeric(11, 8))

    __table_args__ = (
        CheckConstraint(
            "centroid_lat IS NULL OR centroid_lat BETWEEN -90 AND 90", name="check_centroid_lat"
        ),
        CheckConstraint(
            "centroid_lon IS NULL OR centroid_lon BETWEEN -180 AND 180", name="check_centroid_lon"
        ),
    )
