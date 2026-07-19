"""OptimizationJob model — docs/SCHEMA.md §6.3. Async VRP jobs (ARCHITECTURE §3.1)."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from routeopt.models.base import Base, UUIDPrimaryKey


class OptimizationJob(UUIDPrimaryKey, Base):
    __tablename__ = "optimization_jobs"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    trigger: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    input_hash: Mapped[str | None] = mapped_column(String(64))
    solver_strategy: Mapped[str | None] = mapped_column(String(30))
    delivery_count: Mapped[int | None] = mapped_column(Integer)
    vehicle_count: Mapped[int | None] = mapped_column(Integer)
    result: Mapped[dict | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(String)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','running','completed','failed')", name="check_job_status"
        ),
        CheckConstraint("trigger IN ('manual','reoptimize','scheduled')", name="check_job_trigger"),
    )
