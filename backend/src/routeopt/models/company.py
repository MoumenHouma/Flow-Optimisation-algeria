"""Company (tenant) model — docs/SCHEMA.md §3.1."""

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from routeopt.models.base import Base, SoftDelete, Timestamps, UUIDPrimaryKey


class Company(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="free")
    # NULL = unlimited (Enterprise) — see SCHEMA.md §3.1
    max_vehicles: Mapped[int | None] = mapped_column(Integer, default=1)
    max_deliveries_per_day: Mapped[int | None] = mapped_column(Integer, default=10)
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="fr")

    __table_args__ = (
        CheckConstraint("plan IN ('free','starter','pro','enterprise')", name="check_plan"),
        CheckConstraint("locale IN ('fr','ar','ar-dz')", name="check_locale"),
    )
