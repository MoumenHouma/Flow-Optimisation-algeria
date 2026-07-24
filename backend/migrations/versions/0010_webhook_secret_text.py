"""webhooks.secret → Text (encrypted at rest)

Encrypted Fernet tokens exceed VARCHAR(64); widen the column (F16 hardening, L1).

Revision ID: 0010_webhook_secret_text
Revises: 0009_company_branding
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_webhook_secret_text"
down_revision: str | None = "0009_company_branding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "webhooks",
        "secret",
        type_=sa.Text(),
        existing_type=sa.String(64),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "webhooks",
        "secret",
        type_=sa.String(64),
        existing_type=sa.Text(),
        existing_nullable=False,
    )
