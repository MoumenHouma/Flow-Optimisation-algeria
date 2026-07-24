"""companies.branding (F16 white-label)

Per-company appearance config (brand name, primary colour, logo URL) as JSONB
(docs/SCHEMA.md §8.3).

Revision ID: 0009_company_branding
Revises: 0008_territories
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_company_branding"
down_revision: str | None = "0008_territories"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("companies", sa.Column("branding", postgresql.JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "branding")
