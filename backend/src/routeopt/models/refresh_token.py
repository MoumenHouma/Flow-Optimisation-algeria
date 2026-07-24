"""RefreshToken model — docs/SCHEMA.md §3.3. Enables session revocation."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from routeopt.models.base import Base, UUIDPrimaryKey


class RefreshToken(UUIDPrimaryKey, Base):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # All refresh tokens rotated from one login share a family_id. On reuse of an
    # already-rotated token the whole family is revoked (M3, token-reuse detection).
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # SHA-256, never clear
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (UniqueConstraint("token_hash", name="uq_refresh_tokens_hash"),)
