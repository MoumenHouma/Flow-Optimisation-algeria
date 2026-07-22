"""api_keys + webhooks (F10 public API & webhooks)

Partner API keys (docs/SCHEMA.md §3.4) and outbound webhook subscriptions
(docs/SCHEMA.md §3.6).

Revision ID: 0005_api_keys_webhooks
Revises: 0004_reoptimize_route_id
Create Date: 2026-07-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_api_keys_webhooks"
down_revision: str | None = "0004_reoptimize_route_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False, server_default="read"),
        sa.Column("last_used_at", TS),
        sa.Column("expires_at", TS),
        sa.Column("revoked_at", TS),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("scope IN ('read','write','admin')", name="check_scope"),
        sa.UniqueConstraint("key_hash", name="uq_api_keys_hash"),
    )
    op.create_index(
        "idx_api_keys_company",
        "api_keys",
        ["company_id"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )

    op.create_table(
        "webhooks",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("secret", sa.String(64), nullable=False),
        sa.Column("events", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_webhooks_company", "webhooks", ["company_id"])


def downgrade() -> None:
    op.drop_table("webhooks")
    op.drop_table("api_keys")
