"""ProofOfDelivery — one preuve de livraison per delivery (docs/SCHEMA.md §5.3).

Captured by the driver app (F8): a photo and/or signature stored in object
storage (MinIO/S3, ARCHITECTURE §2.5) — only the object *keys* are persisted
here; presigned URLs are minted on read. ``captured_at`` marks the field time.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from routeopt.models.base import Base, UUIDPrimaryKey


class ProofOfDelivery(UUIDPrimaryKey, Base):
    __tablename__ = "proof_of_delivery"

    delivery_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False
    )
    driver_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    # Object-storage keys (not public URLs); presigned on read.
    photo_url: Mapped[str | None] = mapped_column(Text)
    signature_url: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float | None] = mapped_column(Numeric(10, 8))
    lon: Mapped[float | None] = mapped_column(Numeric(11, 8))
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        # One proof per delivery (SCHEMA §5.3) — re-capture overwrites in place.
        UniqueConstraint("delivery_id", name="uq_pod_delivery"),
    )
