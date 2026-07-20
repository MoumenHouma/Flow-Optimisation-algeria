"""proof_of_delivery (F8 driver app)

One proof (photo + signature) per delivery (docs/SCHEMA.md §5.3).

Revision ID: 0003_proof_of_delivery
Revises: 0002_delivery_status_history
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_proof_of_delivery"
down_revision: str | None = "0002_delivery_status_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "proof_of_delivery",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "delivery_id", UUID, sa.ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("driver_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("photo_url", sa.Text),
        sa.Column("signature_url", sa.Text),
        sa.Column("lat", sa.Numeric(10, 8)),
        sa.Column("lon", sa.Numeric(11, 8)),
        sa.Column("captured_at", TS, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("delivery_id", name="uq_pod_delivery"),
    )
    op.create_index("idx_pod_driver", "proof_of_delivery", ["driver_user_id"])


def downgrade() -> None:
    op.drop_table("proof_of_delivery")
