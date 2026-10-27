"""optimization_jobs.trigger allows 'reassign' (F20 blocked-vehicle replan)

A blocked-vehicle redistribution is a distinct trigger from a manual run or a
single-route re-optimization, so webhooks/analytics can tell them apart.

Revision ID: 0016_reassign_trigger
Revises: 0015_fuel
Create Date: 2026-07-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0016_reassign_trigger"
down_revision: str | None = "0015_fuel"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("check_job_trigger", "optimization_jobs", type_="check")
    op.create_check_constraint(
        "check_job_trigger",
        "optimization_jobs",
        "trigger IN ('manual','reoptimize','scheduled','reassign')",
    )


def downgrade() -> None:
    op.drop_constraint("check_job_trigger", "optimization_jobs", type_="check")
    op.create_check_constraint(
        "check_job_trigger",
        "optimization_jobs",
        "trigger IN ('manual','reoptimize','scheduled')",
    )
