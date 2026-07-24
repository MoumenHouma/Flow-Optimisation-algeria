"""territories + deliveries.territory_id (F15 territory management)

Geographic delivery zones (docs/PRD.md §3.3) with a nullable FK from deliveries.

Revision ID: 0008_territories
Revises: 0007_service_time_models
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_territories"
down_revision: str | None = "0007_service_time_models"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "territories",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("color", sa.String(9), nullable=False, server_default="#2563EB"),
        sa.Column("driver_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("centroid_lat", sa.Numeric(10, 8)),
        sa.Column("centroid_lon", sa.Numeric(11, 8)),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", TS),
        sa.CheckConstraint(
            "centroid_lat IS NULL OR centroid_lat BETWEEN -90 AND 90", name="check_centroid_lat"
        ),
        sa.CheckConstraint(
            "centroid_lon IS NULL OR centroid_lon BETWEEN -180 AND 180", name="check_centroid_lon"
        ),
    )
    op.create_index(
        "idx_territories_company",
        "territories",
        ["company_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.add_column(
        "deliveries",
        sa.Column(
            "territory_id",
            UUID,
            sa.ForeignKey("territories.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("deliveries", "territory_id")
    op.drop_table("territories")
