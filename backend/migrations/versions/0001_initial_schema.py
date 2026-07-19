"""initial MVP schema

Creates the MVP-core tables from docs/SCHEMA.md (§3–§6). The generated
``deliveries.geog`` column and its GiST index (§5.1, §8.2) are created with raw
SQL because they are Postgres computed columns not mapped in the ORM.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "companies",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("max_vehicles", sa.Integer, server_default="1"),
        sa.Column("max_deliveries_per_day", sa.Integer, server_default="10"),
        sa.Column("locale", sa.String(10), nullable=False, server_default="fr"),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", TS, nullable=True),
        sa.CheckConstraint("plan IN ('free','starter','pro','enterprise')", name="check_plan"),
        sa.CheckConstraint("locale IN ('fr','ar','ar-dz')", name="check_locale"),
    )

    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30)),
        sa.Column("role", sa.String(50), nullable=False, server_default="manager"),
        sa.Column("locale", sa.String(10), nullable=False, server_default="fr"),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", TS),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", TS, nullable=True),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("role IN ('admin','manager','driver','viewer')", name="check_role"),
    )
    op.create_index(
        "idx_users_company", "users", ["company_id"], postgresql_where=sa.text("deleted_at IS NULL")
    )
    op.create_index(
        "idx_users_role",
        "users",
        ["company_id", "role"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("expires_at", TS, nullable=False),
        sa.Column("revoked_at", TS),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_hash"),
    )
    op.create_index(
        "idx_refresh_tokens_user",
        "refresh_tokens",
        ["user_id"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )

    op.create_table(
        "vehicles",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("driver_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("vehicle_type", sa.String(20), nullable=False, server_default="car"),
        sa.Column("license_plate", sa.String(20)),
        sa.Column("capacity_weight", sa.Numeric(10, 2), nullable=False, server_default="1000"),
        sa.Column("capacity_volume", sa.Numeric(10, 2), nullable=False, server_default="10"),
        sa.Column("depot_lat", sa.Numeric(10, 8), nullable=False),
        sa.Column("depot_lon", sa.Numeric(11, 8), nullable=False),
        sa.Column("depot_address", sa.Text, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", TS, nullable=True),
        sa.CheckConstraint(
            "vehicle_type IN ('car','van','truck','motorcycle')", name="check_vehicle_type"
        ),
        sa.CheckConstraint("capacity_weight >= 0", name="check_capacity_weight"),
        sa.CheckConstraint("capacity_volume >= 0", name="check_capacity_volume"),
        sa.CheckConstraint("depot_lat BETWEEN -90 AND 90", name="check_depot_lat"),
        sa.CheckConstraint("depot_lon BETWEEN -180 AND 180", name="check_depot_lon"),
    )
    op.create_index(
        "idx_vehicles_company",
        "vehicles",
        ["company_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "optimization_jobs",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("requested_by_user_id", UUID, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("trigger", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("input_hash", sa.String(64)),
        sa.Column("solver_strategy", sa.String(30)),
        sa.Column("delivery_count", sa.Integer),
        sa.Column("vehicle_count", sa.Integer),
        sa.Column("result", postgresql.JSONB),
        sa.Column("error_message", sa.Text),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", TS),
        sa.CheckConstraint(
            "status IN ('pending','running','completed','failed')", name="check_job_status"
        ),
        sa.CheckConstraint(
            "trigger IN ('manual','reoptimize','scheduled')", name="check_job_trigger"
        ),
    )
    op.create_index(
        "idx_optimization_jobs_company", "optimization_jobs", ["company_id", "created_at"]
    )
    op.create_index("idx_optimization_jobs_status", "optimization_jobs", ["status"])
    op.create_index("idx_optimization_jobs_input_hash", "optimization_jobs", ["input_hash"])

    op.create_table(
        "routes",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("vehicle_id", UUID, sa.ForeignKey("vehicles.id", ondelete="SET NULL")),
        sa.Column(
            "optimization_job_id", UUID, sa.ForeignKey("optimization_jobs.id", ondelete="SET NULL")
        ),
        sa.Column("name", sa.String(100)),
        sa.Column("total_distance_m", sa.Numeric(10, 2)),
        sa.Column("total_time_s", sa.Integer),
        sa.Column("geometry", postgresql.JSONB),
        sa.Column("status", sa.String(50), nullable=False, server_default="planned"),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("optimized_at", TS),
        sa.Column("deleted_at", TS, nullable=True),
        sa.CheckConstraint(
            "status IN ('planned','dispatched','in_progress','completed','cancelled')",
            name="check_route_status",
        ),
    )
    op.create_index(
        "idx_routes_company",
        "routes",
        ["company_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "idx_routes_vehicle",
        "routes",
        ["vehicle_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "deliveries",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column(
            "company_id", UUID, sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("route_id", UUID, sa.ForeignKey("routes.id", ondelete="SET NULL")),
        sa.Column("order_id", sa.String(100)),
        sa.Column("address", sa.Text, nullable=False),
        sa.Column("address_locale", sa.String(10), nullable=False, server_default="fr"),
        sa.Column("lat", sa.Numeric(10, 8)),
        sa.Column("lon", sa.Numeric(11, 8)),
        sa.Column("geocoding_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("customer_phone", sa.String(30)),
        sa.Column("time_window_start", sa.Time),
        sa.Column("time_window_end", sa.Time),
        sa.Column("service_time", sa.Integer, nullable=False, server_default="300"),
        sa.Column("weight", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("volume", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", TS, nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", TS, nullable=True),
        sa.CheckConstraint("priority IN (1,2,3)", name="check_priority"),
        sa.CheckConstraint(
            "status IN ('pending','geocoded','assigned','en_route',"
            "'delivered','failed','cancelled')",
            name="check_status",
        ),
        sa.CheckConstraint(
            "geocoding_status IN ('pending','matched','approximate','failed')",
            name="check_geocoding_status",
        ),
        sa.CheckConstraint("lat IS NULL OR lat BETWEEN -90 AND 90", name="check_lat"),
        sa.CheckConstraint("lon IS NULL OR lon BETWEEN -180 AND 180", name="check_lon"),
        sa.CheckConstraint("weight >= 0", name="check_weight"),
        sa.CheckConstraint("volume >= 0", name="check_volume"),
        sa.CheckConstraint(
            "time_window_start IS NULL OR time_window_end IS NULL "
            "OR time_window_start <= time_window_end",
            name="check_time_window",
        ),
    )
    op.create_index(
        "idx_deliveries_company_status",
        "deliveries",
        ["company_id", "status"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "idx_deliveries_route",
        "deliveries",
        ["route_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("idx_deliveries_order_id", "deliveries", ["company_id", "order_id"])

    # Generated geospatial column + GiST index (SCHEMA.md §5.1, §8.2)
    op.execute("""
        ALTER TABLE deliveries ADD COLUMN geog GEOGRAPHY(POINT, 4326)
            GENERATED ALWAYS AS (
                CASE WHEN lat IS NOT NULL AND lon IS NOT NULL
                     THEN ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography
                END
            ) STORED
        """)
    op.execute("CREATE INDEX idx_deliveries_geog ON deliveries USING GIST (geog)")

    op.create_table(
        "route_stops",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("route_id", UUID, sa.ForeignKey("routes.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "delivery_id", UUID, sa.ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("eta", TS),
        sa.Column("distance_from_previous_m", sa.Numeric(10, 2)),
        sa.Column("created_at", TS, server_default=sa.func.now()),
        sa.UniqueConstraint("route_id", "sequence", name="uq_route_stops_sequence"),
        sa.UniqueConstraint("route_id", "delivery_id", name="uq_route_stops_delivery"),
    )
    op.create_index("idx_route_stops_route", "route_stops", ["route_id", "sequence"])
    op.create_index("idx_route_stops_delivery", "route_stops", ["delivery_id"])


def downgrade() -> None:
    op.drop_table("route_stops")
    op.execute("DROP INDEX IF EXISTS idx_deliveries_geog")
    op.drop_table("deliveries")
    op.drop_table("routes")
    op.drop_table("optimization_jobs")
    op.drop_table("vehicles")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.drop_table("companies")
