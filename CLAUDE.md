# RouteOpt — project memory

For a fuller session-resume brief (run commands, git/PR state, code map, sales
assets), see [`docs/HANDOFF.md`](docs/HANDOFF.md).

SaaS delivery-route optimizer for the Algerian market. Monorepo:
`backend/` (FastAPI modular monolith), `optimization-worker/` (OR-Tools, DB-free),
`frontend/` (React + Vite + TS). Data: PostgreSQL+PostGIS, Redis, S3/MinIO.
Normative docs live in `docs/` (PRD, ARCHITECTURE, SCHEMA, RULES, DESIGN).

## Status (as of 2026-07-23)

Phases 1–3 delivered — **F1–F16** implemented, tested, green — plus a four-batch
hardening effort (security, optimization correctness, compliance/observability,
ops/CI/docs/tests), the admin audit-log UI, and production deploy artifacts.

**Phase 4 (PRD §3.4, F17–F20) COMPLETE (2026-07-23):** F17 (COD reconciliation),
F18 (live GPS tracking + SMS/WhatsApp notifications + public tracking link),
F19 (SaaS billing + quotas) and F20 (fuel-shortage management) all delivered —
modules `cod` / `tracking` + `notifications` / `billing` / `fuel`, migrations
0013–0015, backend + frontend tests. F18 is migration-free (positions in Redis,
tracking links = signed stateless tokens; SSE via `StreamingResponse`, notif
consumer runs as a lifespan asyncio task). F20 blocked-vehicle replan also shipped
(`POST /routes/{id}/reassign`, migration 0016). Migrations now run **0001 → 0016**.
**The whole PRD roadmap (F1–F20) is now shipped.**

The mega-PR #1 was split into a stacked chain **#2→#5** (#1 closed). ⚠️ The
Phase-4 feature work (F17/F19/F20) landed on the dev branch **after** that split,
so it is **not in any open PR** — the dev branch tip is ahead of PR #5.
(Note the naming clash: PR #5 is titled "Phase 4 — Hardening", which is the
*hardening* batch, not the PRD's F17–F20 Phase 4.)

Development happens on `claude/development-rules-guidelines-nzib0s`.

Verified green (2026-07-23, local PG+Redis): backend **88** pytest (CI gate 70)
· worker **18** pytest (CI gate 75%) · frontend **58** vitest.

## Outstanding — NOT done

These are incomplete. Do not assume they are finished. (The PRD F-list is fully
shipped; the items below are beyond-PRD host actions + one deliberate cleanup.)

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

The DB-backed backend tests need **Postgres + Redis running** (else they error at
setup with connection-refused — that's infra, not a code failure).

- Backend: `cd backend && ruff check . && black --check . && mypy src && TEST_DATABASE_URL=postgresql+asyncpg://routeopt:routeopt@localhost:5432/routeopt pytest`
- Worker: `cd optimization-worker && ruff check . && black --check . && mypy src && pytest`
- Frontend: `cd frontend && npm run lint && npm run typecheck && npm run test -- --run && npm run build`

## Next: beyond the PRD

PRD roadmap F1–F20 is done. Remaining work is post-PRD (see the plan at
`~/.claude/plans/we-continue-working-on-enumerated-metcalfe.md`):
1. Stand up real OSRM + Nominatim locally (clients exist; data + config only).
2. Production deployment to a live host (`docs/DEPLOYMENT.md`, `docker-compose.prod.yml`).
3. Merge the stacked PRs #2→#5 + fold in the Phase-4 feature work.
4. New backlog: driver-PWA offline mutation queue + background sync, turn-by-turn
   nav (needs OSRM), real F19 payment-provider callbacks.
