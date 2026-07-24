"""User model with RBAC role — docs/SCHEMA.md §3.2."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from routeopt.models.base import Base, SoftDelete, Timestamps, UUIDPrimaryKey


class User(UUIDPrimaryKey, Timestamps, SoftDelete, Base):
    __tablename__ = "users"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="manager")
    locale: Mapped[str] = mapped_column(String(10), nullable=False, default="fr")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint("role IN ('admin','manager','driver','viewer')", name="check_role"),
    )
