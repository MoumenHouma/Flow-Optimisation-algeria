# RouteOpt — Session handoff

Read this first in any new session (alongside `CLAUDE.md` at the repo root) to
pick up the project with full context. Snapshot as of **2026-07-24**.

> **2026-07-24 update — go-to-market gap-closing (local, committed, UNPUSHED).**
> A "what's missing before selling" audit closed four sell-blocking gaps
> (commits efeb90d, 4044523, 0a05df8, 0a7b4cb): **A3** password reset (migration
> **0017**, so migrations now run 0001→0017), **A2** demo seed
> (`backend/scripts/seed_demo.py`) + dashboard onboarding checklist, **A4** static
> marketing site (`marketing/`, legal pages are DRAFTS) served by the gateway on
> `routeopt.dz`, **A1** deploy/backup/demo-tunnel scripts (`infra/deploy.sh`,
> `infra/backup.sh`, `infra/demo-tunnel.sh`; cloudflared installed on the PC) +
> `docs/DEPLOYMENT.md` §8-10. Tests: backend **94** pytest, frontend **73** vitest.
> Pitch assets live at `Desktop\routeopt-pitch\` (see §7). Details in `CLAUDE.md`.

---

## 1. What this is

**RouteOpt** — a SaaS delivery-route-optimization platform for the Algerian
last-mile market. Monorepo:

| Path | Stack | Role |
|---|---|---|
| `backend/` | Python 3.11 · FastAPI (modular monolith) · SQLAlchemy 2 · Alembic · PostgreSQL+PostGIS | REST API (auth, orders, fleet, routes, driver, analytics, integrations, predictions, territories, company, audit) |
| `optimization-worker/` | Python 3.11 · OR-Tools · numpy · scikit-learn | DB-free VRP solver; consumes Redis queue, writes results back |
| `frontend/` | React 18 · Vite · TS · Tailwind · React Query · Zustand · MapLibre · vite-plugin-pwa | Manager web app + installable Driver PWA (FR/AR, RTL) |
| `infra/` | OSRM prep, nginx gateway | routing engine + prod reverse proxy |
| `docs/` | — | PRD, ARCHITECTURE, SCHEMA, RULES, DESIGN, DEPLOYMENT, API, WEBHOOKS |

Data layer: PostgreSQL+PostGIS (source of truth), Redis (cache/queue/session),
S3/MinIO (proof-of-delivery photos, exports). Auth: RS256 JWT + rotating
refresh tokens. `docs/SCHEMA.md` is the normative data model.

Repo: **`MoumenHouma/Flow-Optimisation-algeria`**.

---

## 2. Status — DONE

All PRD features **F1–F16** implemented, tested, green, plus a 4-batch hardening
effort and pre-Phase-4 deliverables.

| # | Feature | # | Feature |
|---|---|---|---|
| F1 | CSV/API import + geocoding | F9 | Dynamic re-optimization of live routes |
| F2 | Nominatim geocoding (Algeria-biased, cached) + large-instance K-Means decomposition | F10 | Public API + signed webhooks (HMAC) |
| F3 | VRP optimization (OR-Tools) | F11 | Analytics (trends + performance) |
| F4 | Constraints (capacity, time windows, priority) + ML service-time opt-out | F12 | Multi-dépôt |
| F5 | Route export (PDF/Excel, Arabic shaping) | F13 | ML service-time prediction (cohort) |
| F6 | Manager KPI dashboard | F14 | Multi-objective (distance/time/fuel/CO₂) |
| F7 | Fleet management + greedy fallback timing | F15 | Territories (K-Means zones + driver assignment) |
| F8 | Driver PWA + proof of delivery (photo+signature) | F16 | White-label branding (CSS-var theming) |

**Hardening (from a 3-part audit):**
- Security: 403≠401 semantics, public-API rate limiting, cross-tenant driver validation, prod-config guard, webhook-secret encryption at rest (Fernet).
- Optimization: territories→optimization wiring, K-Means decomposition, objective normalization (km/min/L/kg), fallback timing, ML opt-out.
- Compliance/observability: immutable `audit_log` + admin `GET /audit-log` + admin UI (loi 18-07), refresh-token families with reuse detection + `POST /auth/logout`, Sentry init.
- Ops/CI/docs/tests: worker mypy + coverage gates, README refresh, `docs/DEPLOYMENT.md` / `API.md` / `WEBHOOKS.md`, `docker-compose.prod.yml` + `infra/nginx/` + `.env.prod.example`, more tests.

**Phase 4 (PRD §3.4, F17–F20) — COMPLETE (2026-07-23):**

| # | Feature | Status |
|---|---|---|
| F17 | COD reconciliation (`modules/cod`, `test_cod.py`, frontend `cod/` + test, migration 0013, SCHEMA §9.1) | ✅ done |
| F18 | Real-time GPS tracking + SMS/WhatsApp notifications + tracking link (`modules/tracking` + `modules/notifications`, `test_tracking.py`; migration-free — positions in Redis, links = signed stateless tokens, SSE via `StreamingResponse`, notif consumer = lifespan asyncio task) | ✅ done |
| F19 | SaaS billing + quotas, CCP/BaridiMob (`modules/billing`, `test_billing.py`, frontend `billing/` + test, migration 0014, SCHEMA §9.2) | ✅ done |
| F20 | Fuel-shortage management — vehicle fuel range as an OR-Tools constraint + station availability (`modules/fuel`, `test_fuel.py`, frontend `fuel/` + test, migration 0015, worker `Vehicle.range_m`, SCHEMA §9.3); + blocked-vehicle replan (`POST /routes/{id}/reassign`, `test_reassign.py`, migration 0016) | ✅ done |

Migrations present: **0001 → 0016**. **The full PRD roadmap (F1–F20) is shipped.**

**Verified green (2026-07-23, local PG+Redis up):** backend **88** pytest
(CI gate 70) · worker **18** pytest (CI gate 75%) · frontend **58**
vitest. `ruff`/`black`/`mypy`/`eslint`/`tsc` clean. (The DB-backed backend tests
require Postgres **and** Redis running, or they error at setup — infra, not code.)

---

## 3. Status — NOT done (beyond the PRD)

The PRD F-list (F1–F20) is fully shipped. These beyond-PRD items remain — do
**not** assume they are finished:

1. **Real OSRM + Nominatim in a staging env** — blocked in the cloud sandbox
   (no Docker Hub / Geofabrik access). Config ready (`infra/osrm/prepare.sh`,
   compose `osrm` profile). This is a host action — doable from a machine with
   normal network access.
2. **Production deployment to a live host** — nothing deployed. Runbook +
   artifacts exist (`docs/DEPLOYMENT.md`, `docker-compose.prod.yml`, `infra/nginx/`).
3. **F5 cleanup — remove vestigial top-level `depot`** on the worker's
   `VRPProblem` — deliberate skip (still a real fallback; churn with no behavior change).

(These are also recorded in `CLAUDE.md` at the repo root.)

---

## 4. Git state

- Default/base: `main` (`9243485`, the foundation-docs commit).
- **Development branch:** `claude/development-rules-guidelines-nzib0s`
  (tip carries everything, including this file).
- **Stacked PRs** (review/merge bottom-up, use merge/rebase — **not squash** — to keep the chain):

| PR | Branch | Base | Scope |
|---|---|---|---|
| #2 | `claude/phase-1-mvp` (`92fd824`) | `main` | Phase 1 — MVP (F1–F7) |
| #3 | `claude/phase-2-operations` (`f7fed6d`) | phase-1 | Phase 2 — Operations (F8–F12) |
| #4 | `claude/phase-3-intelligence` (`7e8a4c1`) | phase-2 | Phase 3 — Intelligence & white-label (F13–F16) |
| #5 | `claude/phase-4-hardening` (`38c9dd1`) | phase-3 | Phase 4 — Hardening, compliance & ops |

- PR **#1** (old mega-PR) is **closed** — superseded by the stack.
- The **Phase-4 feature work (F17–F20 + reassign)** landed on the dev branch
  after the split, so the dev branch tip is **ahead of PR #5**. A PR was opened
  2026-07-23 (base `claude/phase-4-hardening` ← dev branch, ~12 commits) via a
  GitHub compare URL — `gh` CLI is installed but **not authed**, so its number/
  state isn't confirmed here; verify on GitHub. (PR #5 is titled "Phase 4 —
  Hardening" — the *hardening* batch, not the PRD's F17–F20 Phase 4; don't
  confuse the two.) These stacked PRs are **not yet merged**.

To continue work, either keep developing on
`claude/development-rules-guidelines-nzib0s`, or branch fresh from `main` once
the stack is merged. Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `ci:`…).

---

## 5. How to run & verify locally

```bash
# Data layer (Docker)
cp .env.example .env
docker compose up -d postgres redis minio

# JWT keys (once) — backend/keys/ is git-ignored
mkdir -p backend/keys && cd backend/keys
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out jwt-private.pem
openssl rsa -in jwt-private.pem -pubout -out jwt-public.pem && cd ../..

# Backend
cd backend && pip install -e ".[dev]" && alembic upgrade head
uvicorn routeopt.main:app --reload --app-dir src      # http://localhost:8000/docs

# Worker (separate shell)
cd optimization-worker && pip install -e ".[dev]" && python -m optimizer.worker

# Frontend (separate shell)
cd frontend && npm install && npm run dev             # http://localhost:5173

# OSRM (optional; needs data — the missing staging step)
./infra/osrm/prepare.sh && docker compose --profile osrm up -d osrm
```

**Verify before any push:**
```bash
cd backend && ruff check . && black --check . && mypy src && \
  TEST_DATABASE_URL=postgresql+asyncpg://routeopt:routeopt@localhost:5432/routeopt pytest
cd optimization-worker && ruff check . && black --check . && mypy src && pytest   # ~2 min (OR-Tools)
cd frontend && npm run lint && npm run typecheck && npm run test -- --run && npm run build
```

---

## 6. Where things live (quick map)

- Optimization engine: `optimization-worker/src/optimizer/` (`solver.py`, `costs.py`, `preprocessor.py` (decomposition), `fallback.py`, `worker.py`).
- Route orchestration: `backend/src/routeopt/modules/routes/` (`service.py` builds the job, `submit_job` / `submit_reoptimize_job`).
- Audit trail: `backend/src/routeopt/core/audit.py` + `modules/audit/`.
- Auth (JWT + refresh families + logout): `backend/src/routeopt/modules/auth/`.
- Config + prod guard: `backend/src/routeopt/config.py`.
- Driver PWA: `frontend/src/features/driver/`; audit UI: `frontend/src/features/settings/AuditLogPage.tsx`.
- Phase 4: `modules/cod` (F17), `modules/billing` (F19), `modules/fuel` (F20);
  fuel range as a solver constraint lives in the worker (`Vehicle.range_m`,
  `optimization-worker/src/optimizer/`); frontend pages `features/cod|billing|fuel/`.

---

## 7. Sales assets produced (not part of the codebase)

Pitch/outreach material for Algerian last-mile carriers, e-commerce fleets,
restaurant chains and pharma distribution. Delivered as files, **not committed**
(not code artifacts). Current set at `Desktop\routeopt-pitch\` (2026-07-24):

- `RouteOpt-GAPS.md` — full "what's missing before selling" audit (A-list blockers,
  B-list later, honesty rules §F).
- `RouteOpt-Emails-Prospection.md` — 4 segment emails + 2 follow-ups + LinkedIn DM.
  Every email asks for a **20-min demo + free pilot**, not a signup (nothing is
  deployed on a permanent URL).
- `RouteOpt-Une-Page.md` — FR one-pager to attach (pitch, real capabilities, DA
  pricing, pilot offer).

Honesty constraints baked into all copy (verified in code): **no Arabic-UI claim**
(the locale toggle only flips layout direction — no translation catalog), **no
automatic SMS/WhatsApp claim** (notification providers are noop/log; only the
tracking *link* is real), **no measured ROI / client counts** (any projection
labelled *illustratif*). An earlier 12-slide `.pptx` existed but is not on this PC;
don't reconstruct company-specific claims — the emails use publicly-known names only.

---

## 8. Next: beyond the PRD (F1–F20 all shipped)

The PRD roadmap is complete. Remaining work is post-PRD (full plan at
`~/.claude/plans/we-continue-working-on-enumerated-metcalfe.md`):
- **Real OSRM + Nominatim locally** — clients already exist
  (`optimization-worker/src/optimizer/distance_matrix.py`,
  `backend/.../modules/orders/geocoding.py`); this is a data build
  (`infra/osrm/prepare.sh`) + config, not new code. Biggest capability unlock.
- **Production deployment** to a live host (`docs/DEPLOYMENT.md`,
  `docker-compose.prod.yml`, `infra/nginx/`).
- **Merge the stacked PRs** #2→#5 and fold in the Phase-4 feature work
  (F17–F20 landed on the dev branch after the split — see §4).
- **Product backlog:** driver-PWA offline mutation queue + background sync,
  turn-by-turn navigation, real F19 payment-provider callbacks, worker-side
  sklearn regressor upgrade for F13 service-time prediction.

---

## Suggested first prompt to resume

> "Read CLAUDE.md and docs/HANDOFF.md. The full PRD roadmap F1–F20 is shipped.
> Stand up real OSRM + Nominatim locally (data build + config; clients already
> exist), then help me merge the stacked PRs. Propose a plan first."
