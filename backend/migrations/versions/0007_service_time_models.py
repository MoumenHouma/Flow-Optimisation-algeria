"""service_time_models (F13 ML service-time prediction)

Per-company trained cohort model for predicting delivery service time.

Revision ID: 0007_service_time_models
Revises: 0006_depots
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_service_time_models"
down_revision: str | None = "0006_depots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "service_time_models",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("model", postgresql.JSONB, nullable=False),
        sa.Column("sample_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cohort_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("global_median_s", sa.Integer, nullable=False, server_default="300"),
        sa.Column("mae_seconds", sa.Numeric(10, 2)),
        sa.Column("trained_at", TS, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", name="uq_service_time_models_company"),
    )


def downgrade() -> None:
    op.drop_table("service_time_models")
