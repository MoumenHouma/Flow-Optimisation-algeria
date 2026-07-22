"""Webhook model — outbound event subscriptions (F10, docs/SCHEMA.md §3.6).

A company registers an endpoint URL and the events it wants. RouteOpt POSTs a
JSON payload signed with the webhook's ``secret`` (HMAC-SHA256) on each event.
``events`` is a comma-separated allowlist (e.g. "delivery.status_changed").
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from routeopt.models.base import Base


class Webhook(Base):
    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    # Encrypted at rest (Fernet); decrypted only to sign outgoing payloads.
    secret: Mapped[str] = mapped_column(Text, nullable=False)
    events: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
