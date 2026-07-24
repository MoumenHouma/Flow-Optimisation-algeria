"""optimization_jobs.reoptimize_route_id (F9 dynamic re-optimization)

Links a trigger='reoptimize' job to the live route whose remaining stops it
re-plans (docs/SCHEMA.md §6.3).

Revision ID: 0004_reoptimize_route_id
Revises: 0003_proof_of_delivery
Create Date: 2026-07-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_reoptimize_route_id"
down_revision: str | None = "0003_proof_of_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column(
        "optimization_jobs",
        sa.Column(
            "reoptimize_route_id",
            UUID,
            sa.ForeignKey("routes.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("optimization_jobs", "reoptimize_route_id")
