# RouteOpt — Session handoff

Read this first in any new session (alongside `CLAUDE.md` at the repo root) to
pick up the project with full context. Snapshot as of **2026-07-23**.

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

**Phase 4 (PRD §3.4, F17–F20) — in progress:**

| # | Feature | Status |
|---|---|---|
| F17 | COD reconciliation (`modules/cod`, `test_cod.py`, frontend `cod/` + test, migration 0013, SCHEMA §9.1) | ✅ done |
| F18 | Real-time GPS tracking + SMS/WhatsApp notifications + tracking link | ❌ **not done** (no module) |
| F19 | SaaS billing + quotas, CCP/BaridiMob (`modules/billing`, `test_billing.py`, frontend `billing/` + test, migration 0014, SCHEMA §9.2) | ✅ done |
| F20 | Fuel-shortage management — vehicle fuel range as an OR-Tools constraint + station availability (`modules/fuel`, `test_fuel.py`, frontend `fuel/` + test, migration 0015, worker `Vehicle.range_m`, SCHEMA §9.3) | ✅ done |

Migrations present: **0001 → 0015**.

**Verified green (2026-07-23, local PG+Redis up):** backend **84** pytest
(77% cov, CI gate 70) · worker **18** pytest (CI gate 75%) · frontend **55**
vitest. `ruff`/`black`/`mypy`/`eslint`/`tsc` clean. (The DB-backed backend tests
require Postgres **and** Redis running, or they error at setup — infra, not code.)

---

## 3. Status — NOT done (before Phase 4)

Do **not** assume these are finished:

0. **F18 — real-time tracking + notifications** (the remaining Phase 4 feature) —
   live driver GPS on the map + SMS/WhatsApp "en approche" alerts + public
   tracking link (PRD §3.4). No module yet.
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
- ⚠️ **The Phase-4 feature work (F17/F19/F20) is not in any open PR.** It landed
  on the dev branch after the split, so the dev branch tip is **ahead of PR #5**.
  (PR #5 is titled "Phase 4 — Hardening" — that's the *hardening* batch, not the
  PRD's F17–F20 Phase 4; don't confuse the two.) If you want these reviewed,
  open a new PR from the dev branch, or fold them into the stack.

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

A pitch deck and prospection emails were produced for outreach to Algerian
last-mile carriers. They were delivered to the user as files and are **not
committed to this repo** (they aren't code artifacts):

- `RouteOpt-Presentation.pptx` — 12-slide French pitch deck for Algerian carriers.
- `RouteOpt-Emails-Prospection.md` — 6 tailored prospection emails
  (Yalidine, Maystro, ZR Express, NOEST, GuepEX, Colivraison Express).

Notes if regenerating: the deck's ROI figures are labelled *illustratif*
(index, base 100), not measured; contact details are placeholders (`[...]`);
built with `pptxgenjs` + `react-icons`/`sharp` for icons; market stats sourced
from public research (easysellapp.com, dzbuild.com, ministère de la Poste —
cahier des charges 2025–2026).

---

## 8. Next: finish Phase 4 (F17/F19/F20 done, F18 remaining)

From `docs/PRD.md` §3.4:
- **F18 — real-time tracking + notifications** (the only Phase 4 feature left):
  live driver GPS on the manager map, SMS/WhatsApp "en approche" client alerts,
  and a public tracking link. Reduces client-call load (PRD §2.1).
- (Optional follow-ups) wire real payment-provider callbacks into F19 billing;
  worker-side sklearn regressor upgrade for F13 service-time prediction.

Beyond Phase 4 (product backlog, not in the PRD's F-list): driver-PWA offline
mutation queue + background sync, turn-by-turn navigation.

---

## Suggested first prompt to resume

> "Read CLAUDE.md and docs/PRD.md §3.4. F1–F16 + hardening + Phase 4 F17/F19/F20
> are done (see docs/HANDOFF.md). Implement the last Phase 4 feature, **F18**
> (live GPS tracking + SMS/WhatsApp notifications + tracking link). Propose a
> plan first."
