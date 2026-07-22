"""vehicles fuel columns + fuel_stations (F20 fuel-shortage management)

Adds ``vehicles.fuel_range_km`` / ``fuel_type`` (range feeds the OR-Tools range
constraint) and the ``fuel_stations`` table with live availability. PRD §4.1
"pénurie carburant", docs/SCHEMA.md §10.

Revision ID: 0012_fuel
Revises: 0011_billing
Create Date: 2026-07-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_fuel"
down_revision: str | None = "0011_billing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column("vehicles", sa.Column("fuel_range_km", sa.Numeric(8, 2), nullable=True))
    op.add_column(
        "vehicles",
        sa.Column("fuel_type", sa.String(20), nullable=False, server_default="essence"),
    )
    op.create_check_constraint(
        "check_fuel_type", "vehicles", "fuel_type IN ('essence','diesel','gpl','electric')"
    )
    op.create_check_constraint(
        "check_fuel_range", "vehicles", "fuel_range_km IS NULL OR fuel_range_km > 0"
    )

    op.create_table(
        "fuel_stations",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "company_id",
            UUID,
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("lat", sa.Numeric(10, 8), nullable=False),
        sa.Column("lon", sa.Numeric(11, 8), nullable=False),
        sa.Column("fuel_types", sa.String(100), nullable=False, server_default="essence"),
        sa.Column("status", sa.String(20), nullable=False, server_default="available"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('available','shortage','closed')", name="check_station_status"
        ),
        sa.CheckConstraint("lat BETWEEN -90 AND 90", name="check_station_lat"),
        sa.CheckConstraint("lon BETWEEN -180 AND 180", name="check_station_lon"),
    )
    op.create_index("ix_fuel_stations_company", "fuel_stations", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_fuel_stations_company", table_name="fuel_stations")
    op.drop_table("fuel_stations")
    op.drop_constraint("check_fuel_range", "vehicles", type_="check")
    op.drop_constraint("check_fuel_type", "vehicles", type_="check")
    op.drop_column("vehicles", "fuel_type")
    op.drop_column("vehicles", "fuel_range_km")
