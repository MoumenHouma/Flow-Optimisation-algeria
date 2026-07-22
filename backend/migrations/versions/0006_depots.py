"""depots + vehicles.depot_id (F12 multi-dépôt)

Company depots (docs/SCHEMA.md §4.2) and a nullable FK from vehicles. Inline
vehicle depot columns are kept as the resolved coordinates (SCHEMA §8.1).

Revision ID: 0006_depots
Revises: 0005_api_keys_webhooks
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_depots"
down_revision: str | None = "0005_api_keys_webhooks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "depots",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("lat", sa.Numeric(10, 8), nullable=False),
        sa.Column("lon", sa.Numeric(11, 8), nullable=False),
        sa.Column("address", sa.Text, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", TS),
        sa.CheckConstraint("lat BETWEEN -90 AND 90", name="check_depot_lat"),
        sa.CheckConstraint("lon BETWEEN -180 AND 180", name="check_depot_lon"),
    )
    op.create_index(
        "idx_depots_company",
        "depots",
        ["company_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.add_column(
        "vehicles",
        sa.Column("depot_id", UUID, sa.ForeignKey("depots.id", ondelete="SET NULL"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vehicles", "depot_id")
    op.drop_table("depots")
