# RouteOpt — project memory

SaaS delivery-route optimizer for the Algerian market. Monorepo:
`backend/` (FastAPI modular monolith), `optimization-worker/` (OR-Tools, DB-free),
`frontend/` (React + Vite + TS). Data: PostgreSQL+PostGIS, Redis, S3/MinIO.
Normative docs live in `docs/` (PRD, ARCHITECTURE, SCHEMA, RULES, DESIGN).

## Status (as of 2026-07-22)

Phases 1–3 delivered — **F1–F16** implemented, tested, green. A four-batch
hardening effort (security, optimization correctness, compliance/observability,
ops/CI/docs/tests), the admin audit-log UI, and production deploy artifacts are
also done. The original mega-PR #1 was split into a stacked chain **#2→#5**
(Phase 1→4) and #1 was closed.

Development happens on `claude/development-rules-guidelines-nzib0s` (its tip
equals PR #5 / `claude/phase-4-hardening`).

## Outstanding — NOT done (before Phase 4)

These are intentionally incomplete. Do not assume they are finished.

1. **Stand up real OSRM + Nominatim in a staging environment** — NOT done.
   Blocked in the build sandbox (network policy blocks Docker Hub / Geofabrik).
   Config is ready (`infra/osrm/prepare.sh`, compose `osrm` profile, prod env
   points at a self-hosted Nominatim); the actual data build + run is a host
   action that must be performed where network access exists.

2. **Production deployment to a live host** — NOT done.
   No target host or secrets store is reachable from the sandbox. The full
   runbook exists in `docs/DEPLOYMENT.md` and the artifacts exist
   (`docker-compose.prod.yml`, `infra/nginx/`, `.env.prod.example`), but nothing
   has actually been deployed.

3. **F5 cleanup — remove the vestigial top-level `depot`** on
   `optimization-worker` `VRPProblem` — NOT done (deliberate skip).
   `problem.depot` still serves as a real fallback in `worker.py`; removing it is
   broad churn (dataclass + solver + worker + every test payload) with no
   behavior change. Revisit only if the field genuinely becomes dead.

## Verify (before any push)

- Backend: `cd backend && ruff check . && black --check . && mypy src && TEST_DATABASE_URL=postgresql+asyncpg://routeopt:routeopt@localhost:5432/routeopt pytest`
- Worker: `cd optimization-worker && ruff check . && black --check . && mypy src && pytest`
- Frontend: `cd frontend && npm run lint && npm run typecheck && npm run test -- --run && npm run build`

## Next: Phase 4 (not started)

Payments (CCP/BaridiMob), driver-PWA offline mutation queue + background sync,
turn-by-turn navigation. See `docs/PRD.md`.
