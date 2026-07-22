"""cod_payments + deliveries COD columns (F17 cash-on-delivery)

Adds ``deliveries.cod_amount`` / ``cod_currency`` (order total due at the stop,
set at import) and the ``cod_payments`` reconciliation table (cash the driver
actually collected). docs/SCHEMA.md §5.4, PRD §4.1.

Revision ID: 0013_cod_payments
Revises: 0012_refresh_token_family
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_cod_payments"
down_revision: str | None = "0012_refresh_token_family"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("deliveries", sa.Column("cod_amount", sa.Numeric(12, 2), nullable=True))
    op.add_column(
        "deliveries",
        sa.Column("cod_currency", sa.String(3), nullable=False, server_default="DZD"),
    )
    op.create_check_constraint(
        "check_cod_amount", "deliveries", "cod_amount IS NULL OR cod_amount >= 0"
    )

    op.create_table(
        "cod_payments",
        sa.Column(
            "id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "company_id",
            UUID,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "delivery_id",
            UUID,
            sa.ForeignKey("deliveries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "route_id",
            UUID,
            sa.ForeignKey("routes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "driver_user_id",
            UUID,
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("amount_expected", sa.Numeric(12, 2), nullable=True),
        sa.Column("amount_collected", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="DZD"),
        sa.Column("method", sa.String(20), nullable=False, server_default="cash"),
        sa.Column("status", sa.String(20), nullable=False, server_default="collected"),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("delivery_id", name="uq_cod_delivery"),
        sa.CheckConstraint("method IN ('cash','baridimob','ccp','none')", name="check_cod_method"),
        sa.CheckConstraint(
            "status IN ('pending','collected','reconciled','discrepancy')",
            name="check_cod_status",
        ),
        sa.CheckConstraint("amount_collected >= 0", name="check_cod_collected"),
        sa.CheckConstraint(
            "amount_expected IS NULL OR amount_expected >= 0", name="check_cod_expected"
        ),
    )
    op.create_index("ix_cod_payments_company", "cod_payments", ["company_id"])
    op.create_index("ix_cod_payments_route", "cod_payments", ["route_id"])


def downgrade() -> None:
    op.drop_index("ix_cod_payments_route", table_name="cod_payments")
    op.drop_index("ix_cod_payments_company", table_name="cod_payments")
    op.drop_table("cod_payments")
    op.drop_constraint("check_cod_amount", "deliveries", type_="check")
    op.drop_column("deliveries", "cod_currency")
    op.drop_column("deliveries", "cod_amount")
