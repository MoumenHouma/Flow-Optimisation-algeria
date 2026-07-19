# RouteOpt — Optimiseur de Tournées de Livraison (Algérie)

> Plateforme SaaS d'optimisation de tournées de livraison conçue pour le marché algérien.
> Voir [`docs/`](./docs) pour le PRD, l'architecture, le design system, les règles de dev et le schéma de données.

## Architecture (résumé)

Monorepo — **modular monolith** (ADR-004) :

| Composant | Techno | Rôle |
|---|---|---|
| [`backend/`](./backend) | Python 3.11 · FastAPI · SQLAlchemy 2 · Alembic | API REST (Auth, Orders, Fleet, Routes) |
| [`optimization-worker/`](./optimization-worker) | Python 3.11 · OR-Tools · OSRM client | Résolution VRP asynchrone (queue Redis) |
| [`frontend/`](./frontend) | React 18 · Vite · TS · Tailwind · shadcn/ui · MapLibre | Web app manager + Driver PWA |
| [`infra/`](./infra) | OSRM · Nginx | Routing engine self-hosted + reverse proxy |

Data layer : **PostgreSQL + PostGIS** (source de vérité), **Redis** (cache/queue/session), **MinIO/S3** (fichiers, preuves de livraison).

Le schéma complet est normatif dans [`docs/SCHEMA.md`](./docs/SCHEMA.md).

## Démarrage rapide (local)

```bash
cp .env.example .env
docker compose up -d postgres redis minio        # data layer
# Préparer OSRM (une fois, ~8-16 GB RAM) :
./infra/osrm/prepare.sh
docker compose up -d osrm
# Backend + worker + frontend :
docker compose up --build
```

- API : http://localhost:8000 — docs Swagger : http://localhost:8000/docs
- Frontend : http://localhost:5173
- OSRM : http://localhost:5000

## Développement

```bash
# Backend
cd backend && pip install -e ".[dev]"
alembic upgrade head
uvicorn routeopt.main:app --reload

# Optimization worker
cd optimization-worker && pip install -e ".[dev]"
python -m optimizer.worker

# Frontend
cd frontend && npm install && npm run dev
```

Qualité (cf. [`docs/RULES.md`](./docs/RULES.md)) : `ruff`, `mypy`, `black`, `pytest` (Python) · `eslint`, `prettier`, `vitest` (TS). Commits en [Conventional Commits](./docs/RULES.md#12-commit-convention-conventional-commits).

## Statut

MVP en cours (Phase 1, F1–F7). Voir la roadmap dans [`docs/PRD.md`](./docs/PRD.md#3-fonctionnalités--mvp--roadmap).
