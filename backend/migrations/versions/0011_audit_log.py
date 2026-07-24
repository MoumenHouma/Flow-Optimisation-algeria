"""audit_log immutable audit trail (H2 — CNIL loi 18-07, SCHEMA §3.5)

Append-only journal of sensitive actions. BIGSERIAL PK (high-volume, no UUID).

Revision ID: 0011_audit_log
Revises: 0010_webhook_secret_text
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_audit_log"
down_revision: str | None = "0010_webhook_secret_text"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("company_id", UUID, sa.ForeignKey("companies.id", ondelete="SET NULL")),
        sa.Column("actor_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", UUID),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("ip_address", postgresql.INET),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_audit_log_company_created", "audit_log", ["company_id", "created_at"])
    op.create_index("idx_audit_log_resource", "audit_log", ["resource_type", "resource_id"])


def downgrade() -> None:
    op.drop_index("idx_audit_log_resource", table_name="audit_log")
    op.drop_index("idx_audit_log_company_created", table_name="audit_log")
    op.drop_table("audit_log")
