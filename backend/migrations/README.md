# Migrations (Alembic)

The schema is normative in [`../../docs/SCHEMA.md`](../../docs/SCHEMA.md). Every
schema change must ship with a migration here (docs/SCHEMA.md closing note).

```bash
# Generate a migration from model changes
alembic revision --autogenerate -m "add refresh_tokens table"

# Apply
alembic upgrade head

# Roll back one
alembic downgrade -1
```

> First migration must enable PostGIS: `op.execute("CREATE EXTENSION IF NOT EXISTS postgis")`
> before creating `deliveries.geog` (docs/SCHEMA.md §5.1, §8.2).
