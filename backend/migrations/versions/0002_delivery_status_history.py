"""delivery_status_history (F8 driver app)

Append-only status trail for deliveries (docs/SCHEMA.md §5.2).

Revision ID: 0002_delivery_status_history
Revises: 0001_initial_schema
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_delivery_status_history"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "delivery_status_history",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "delivery_id", UUID, sa.ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("from_status", sa.String(50)),
        sa.Column("to_status", sa.String(50), nullable=False),
        sa.Column("reason", sa.String(100)),
        sa.Column("changed_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("lat", sa.Numeric(10, 8)),
        sa.Column("lon", sa.Numeric(11, 8)),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "idx_delivery_status_history_delivery",
        "delivery_status_history",
        ["delivery_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("delivery_status_history")
