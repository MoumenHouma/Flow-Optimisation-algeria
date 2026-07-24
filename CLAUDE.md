# RouteOpt — project memory

For a fuller session-resume brief (run commands, git/PR state, code map, sales
assets), see [`docs/HANDOFF.md`](docs/HANDOFF.md).

SaaS delivery-route optimizer for the Algerian market. Monorepo:
`backend/` (FastAPI modular monolith), `optimization-worker/` (OR-Tools, DB-free),
`frontend/` (React + Vite + TS). Data: PostgreSQL+PostGIS, Redis, S3/MinIO.
Normative docs live in `docs/` (PRD, ARCHITECTURE, SCHEMA, RULES, DESIGN).

## Status (as of 2026-07-24)

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

## Go-to-market gap-closing (2026-07-24, local, committed, UNPUSHED)

A repo audit for "what's missing before selling" found the product code was fine;
the go-to-market envelope wasn't. Four sell-blocking gaps closed (commits efeb90d,
4044523, 0a05df8, 0a7b4cb — all local, need fetch+rebase+push on the shared branch):

- **A3 password reset** (efeb90d): `password_reset_tokens` (migration **0017**,
  SCHEMA §3.7) + `/auth/forgot-password` (always 202, no enumeration, IP-throttled)
  + `/auth/reset-password` (single-use, revokes ALL sessions). `core/email.py`
  provider (noop|log|smtp, default log → link in backend log). Frontend
  `/forgot-password` + `/reset-password`. Backend **94** pytest, frontend **73** vitest.
- **A2 demo seed + onboarding** (4044523): `backend/scripts/seed_demo.py`
  (idempotent; demo@routeopt.dz / demo-pass-123, 3 vehicles, 15 Alger deliveries;
  submits one optimization → completed route, verified 15 stops / 95.1 km /
  3974-pt OSRM geometry; degrades gracefully if worker down). `OnboardingChecklist`
  on the dashboard (drives off dashboard summary, no new endpoint).
- **A4 vitrine + legal** (0a05df8): static `marketing/` (index + cgu/confidentialite/
  mentions-legales — legal pages are DRAFTS w/ visible banner, need a lawyer).
  Served by the gateway on `routeopt.dz` (app stays `app.routeopt.dz`).
- **A1 reachability** (0a7b4cb): `infra/deploy.sh` (VPS), `infra/backup.sh` (cron
  pg_dump+S3), `infra/demo-tunnel.sh` (Cloudflare quick tunnel — cloudflared now
  INSTALLED on PC via winget; tunnel verified end-to-end). DEPLOYMENT §8-10.

Pitch assets (NOT in repo, on Desktop\routeopt-pitch\): `RouteOpt-GAPS.md`,
`RouteOpt-Emails-Prospection.md` (4 segments + follow-ups), `RouteOpt-Une-Page.md`.
Honesty constraints enforced: no Arabic-UI claim (catalog doesn't exist), no
automatic SMS claim (providers are noop/log — only the tracking link is real),
no measured ROI.

## Outstanding — NOT done

These are incomplete. Do not assume they are finished.

1. **Production deployment to a live host** — still NOT done. Scripts + runbook
   now exist (`infra/deploy.sh`, `docs/DEPLOYMENT.md` §8-10) but need the user's
   VPS + domain + secrets; nothing is deployed. `infra/demo-tunnel.sh` is the
   stopgap for a live demo from the PC.

2. **Self-hosted Nominatim** — NOT done (real OSRM Algeria IS live locally).
   Geocoding still uses the public ~1 req/s instance.

3. **Deferred by scope (in RouteOpt-GAPS.md §B):** Arabic translation catalog,
   real SMS/WhatsApp gateway, in-app turn-by-turn, merging stacked PRs #2→#5,
   F20 single-vehicle range fallback ignores the constraint, UTC-vs-Alger quota
   boundary, "0 DA/mois" Enterprise label.

4. **F5 cleanup — remove the vestigial top-level `depot`** on
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
