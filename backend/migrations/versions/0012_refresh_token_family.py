"""refresh_tokens.family_id for token-reuse detection (M3)

Groups all tokens rotated from one login into a family so a replayed token can
revoke the whole chain. Existing rows get a fresh per-row family via
gen_random_uuid(); the server default is then dropped (app always sets it).

Revision ID: 0012_refresh_token_family
Revises: 0011_audit_log
Create Date: 2026-07-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_refresh_token_family"
down_revision: str | None = "0011_audit_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column(
        "refresh_tokens",
        sa.Column("family_id", UUID, nullable=False, server_default=sa.text("gen_random_uuid()")),
    )
    op.alter_column("refresh_tokens", "family_id", server_default=None)
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "family_id")
