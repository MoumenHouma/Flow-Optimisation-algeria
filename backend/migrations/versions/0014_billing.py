"""subscriptions + invoices (F19 SaaS billing)

Records a company's paid plan (subscriptions) and its billing charges
(invoices, one per YYYY-MM period). Amounts in DZD (PRD §5.1). docs/SCHEMA.md §9.

Revision ID: 0014_billing
Revises: 0013_cod_payments
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_billing"
down_revision: str | None = "0013_cod_payments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "company_id",
            UUID,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("plan", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("amount_da", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("plan IN ('free','starter','pro','enterprise')", name="check_sub_plan"),
        sa.CheckConstraint("status IN ('active','canceled')", name="check_sub_status"),
        sa.CheckConstraint("amount_da >= 0", name="check_sub_amount"),
    )
    op.create_index("ix_subscriptions_company", "subscriptions", ["company_id"])

    op.create_table(
        "invoices",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "company_id",
            UUID,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subscription_id",
            UUID,
            sa.ForeignKey("subscriptions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False),
        sa.Column("amount_da", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("method", sa.String(20), nullable=True),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("company_id", "period", name="uq_invoice_company_period"),
        sa.CheckConstraint("status IN ('pending','paid','void')", name="check_invoice_status"),
        sa.CheckConstraint(
            "method IS NULL OR method IN ('cash','ccp','baridimob','stripe')",
            name="check_invoice_method",
        ),
        sa.CheckConstraint("amount_da >= 0", name="check_invoice_amount"),
    )
    op.create_index("ix_invoices_company", "invoices", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_invoices_company", table_name="invoices")
    op.drop_table("invoices")
    op.drop_index("ix_subscriptions_company", table_name="subscriptions")
    op.drop_table("subscriptions")
