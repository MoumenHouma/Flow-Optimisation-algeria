# RouteOpt

**Delivery route optimization SaaS for companies in Algeria: import orders, get optimized routes for every vehicle in seconds, and track deliveries live.**

Python · FastAPI · Google OR-Tools · PostgreSQL + PostGIS · Redis · React + TypeScript · MapLibre · OSRM

<!-- Add 2–3 screenshots here: optimized routes on the map, analytics page, driver app.
     Example: ![Optimized routes](docs/screenshots/routes.png) -->

---

## The problem

Delivery companies plan routes by hand or by habit. Drivers cross each other's zones, vehicles leave half empty or overloaded, time windows are missed, and fuel costs climb. With cash-on-delivery, every failed or late delivery also means money not collected.

## What RouteOpt does

1. **Import** deliveries from a CSV file; addresses are geocoded automatically.
2. **Optimize**: the solver assigns deliveries to vehicles and orders the stops, respecting each vehicle's capacity, each customer's time window and each vehicle's fuel range.
3. **Dispatch**: each driver gets a mobile web app with their route, proof of delivery (photo, signature) and offline support.
4. **Track and adjust**: live tracking, customer tracking links, re-optimization when the day changes, cash-on-delivery reconciliation.
5. **Learn**: analytics on performance, and service times predicted from past deliveries.

## The optimization engine

The core is a **Capacitated Vehicle Routing Problem with Time Windows** (CVRPTW), solved with Google OR-Tools in a separate worker process:

| Element | How it is modeled |
| --- | --- |
| Objective | Weighted sum of **distance, time, fuel and CO₂**, computed per vehicle type. The company chooses the weights. |
| Capacity | Capacity dimension per vehicle |
| Time windows | Time dimension with each delivery's window and a predicted service time |
| Fuel range | Range dimension capping each vehicle's total route distance |
| Search | Path-cheapest-arc first solution, improved with **Guided Local Search** under a time limit |
| Large instances | Split into sub-problems with **K-Means clustering** before solving |
| Road distances | Self-hosted **OSRM** routing engine on the Algeria road network |
| Fallbacks | Without OSRM, straight-line (haversine) distances are used. If the solver finds no solution in time, a nearest-neighbor heuristic still returns routes. Both are flagged as suboptimal |

**Service-time prediction:** instead of a fixed 5 minutes per stop, RouteOpt learns typical on-site durations from delivery history, grouped by cohort, with fallbacks to the global median and then to a default. Better service times give more realistic routes.

Solver code: [`optimization-worker/src/optimizer/`](optimization-worker/src/optimizer/).

## Features (F1–F16 delivered)

| # | Feature | # | Feature |
|---|---|---|---|
| F1 | Delivery import and geocoding | F9 | Dynamic re-optimization of a route |
| F2 | Large-instance decomposition (K-Means) | F10 | Public API and HMAC-signed webhooks |
| F3 | Multi-objective VRP optimization | F11 | Analytics (trends and performance) |
| F4 | Constraints (capacity, time windows) | F12 | Multiple depots |
| F5 | Route export (PDF / Excel) | F13 | Predicted service time (ML per cohort) |
| F6 | Real-time delivery tracking | F14 | Weighted objectives (distance / time / fuel / CO₂) |
| F7 | Offline greedy fallback (haversine) | F15 | Territories (zones and driver assignment) |
| F8 | Driver PWA with proof of delivery | F16 | White label (theme per company) |

Also included: cash-on-delivery reconciliation, billing plans, fuel management, password reset, audit log.

## Security and quality

- Multi-tenant isolation, role-based access control, API keys hashed (SHA-256), webhook secrets encrypted (Fernet), rate limiting per plan, immutable audit log (Algerian data protection law 18-07), session revocation through refresh-token families.
- **Tested:** more than 100 Python tests (backend and solver) and about 70 frontend tests.
- **CI on every push** ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)): ruff, black, mypy and pytest for the backend (minimum 70 % coverage) and the solver (minimum 75 %), plus lint, type-check, tests and build for the frontend.

## Architecture

Modular monolith in one repository:

| Component | Tech | Role |
|---|---|---|
| [`backend/`](backend) | Python 3.11 · FastAPI · SQLAlchemy 2 · Alembic | REST API (auth, orders, fleet, routes, analytics…) |
| [`optimization-worker/`](optimization-worker) | Python 3.11 · OR-Tools · OSRM client · scikit-learn | Asynchronous VRP solving from a Redis queue |
| [`frontend/`](frontend) | React 18 · Vite · TypeScript · Tailwind · shadcn/ui · MapLibre | Manager web app and driver PWA |
| [`infra/`](infra) | OSRM · Nginx | Self-hosted routing engine and reverse proxy |

Data: **PostgreSQL + PostGIS** (source of truth), **Redis** (cache, queue, sessions), **MinIO / S3** (files, proofs of delivery).

## Run it locally

```bash
cp .env.example .env
docker compose up -d postgres redis minio        # data layer

# Prepare OSRM once (~8–16 GB RAM for Algeria):
./infra/osrm/prepare.sh                           # or: REGION=monaco CONTINENT=europe ./infra/osrm/prepare.sh
docker compose --profile osrm up -d osrm          # OSRM_FILE in .env must match the region

# Backend + worker + frontend:
docker compose up --build
```

Without OSRM, optimization still works with the straight-line fallback (result flagged `is_suboptimal`). Check connectivity with `GET /health/ready`.

- API: http://localhost:8000 (Swagger docs at `/docs`)
- Frontend: http://localhost:5173

**Demo data** (manager `demo@routeopt.dz` / `demo-pass-123`, a fleet, deliveries in Algiers and one optimized route):

```bash
cd backend && python scripts/seed_demo.py     # idempotent; never run on real data
```

### Development and tests

```bash
# Backend
cd backend && pip install -e ".[dev]" && alembic upgrade head
uvicorn routeopt.main:app --reload
TEST_DATABASE_URL=postgresql+asyncpg://routeopt:routeopt@localhost:5432/routeopt pytest --cov=src

# Optimization worker
cd optimization-worker && pip install -e ".[dev]"
python -m optimizer.worker
pytest

# Frontend
cd frontend && npm install && npm run dev
npm run lint && npm run typecheck && npm run test -- --run && npm run build
```

## Documentation

Product requirements, architecture, data schema, partner API, webhooks and deployment are in [`docs/`](docs) (French): [PRD](docs/PRD.md) · [Architecture](docs/ARCHITECTURE.md) · [Schema](docs/SCHEMA.md) · [API](docs/API.md) · [Webhooks](docs/WEBHOOKS.md) · [Deployment](docs/DEPLOYMENT.md).

## Author

**Abdelmoumen Houma**: data analyst and developer, Master's in Operations Research.
I build optimization and analytics into real business software: routing, scheduling, forecasting, dashboards.
[LinkedIn](https://linkedin.com/in/abdelmoumen-houma-806405399) · [GitHub](https://github.com/moumenhouma) <!-- add your Upwork profile link -->
