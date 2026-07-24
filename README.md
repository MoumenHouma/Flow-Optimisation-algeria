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

# Préparer OSRM (une fois, ~8-16 GB RAM pour l'Algérie) :
./infra/osrm/prepare.sh                           # ou: REGION=monaco CONTINENT=europe ./infra/osrm/prepare.sh
docker compose --profile osrm up -d osrm          # OSRM_FILE dans .env doit matcher la région

# Backend + worker + frontend :
docker compose up --build
```

> Sans OSRM, l'optimisation fonctionne quand même : le worker retombe sur une
> approximation à vol d'oiseau (résultat marqué `is_suboptimal`, PRD §4.3).
> Vérifier la connectivité : `GET /health/ready` (rapporte database / redis / osrm).

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

### Données de démonstration

Pour peupler une instance vide (démo, test) avec une société cliquable
(gérant `demo@routeopt.dz` / `demo-pass-123`, flotte + livraisons Alger, une
tournée optimisée) :

```bash
cd backend && python scripts/seed_demo.py     # idempotent ; ne pas lancer sur des données réelles
```

Qualité (cf. [`docs/RULES.md`](./docs/RULES.md)) : `ruff`, `mypy`, `black`, `pytest` (Python) · `eslint`, `prettier`, `vitest` (TS). Commits en [Conventional Commits](./docs/RULES.md#12-commit-convention-conventional-commits).

### Tests

```bash
# Backend (les tests d'intégration DB tournent quand TEST_DATABASE_URL est défini)
cd backend
TEST_DATABASE_URL=postgresql+asyncpg://routeopt:routeopt@localhost:5432/routeopt \
  pytest --cov=src            # ruff check . · black --check . · mypy src

# Optimization worker (OR-Tools requis)
cd optimization-worker && pytest      # ruff check . · black --check . · mypy src

# Frontend
cd frontend && npm run lint && npm run typecheck && npm run test -- --run && npm run build
```

La CI ([`.github/workflows/ci.yml`](./.github/workflows/ci.yml)) applique lint + types + tests + seuils de couverture sur chaque composant.

## Statut

Phases 1–3 livrées : **F1–F16** implémentés.

| # | Fonctionnalité | # | Fonctionnalité |
|---|---|---|---|
| F1 | Import + géocodage des livraisons | F9 | Ré-optimisation dynamique d'une tournée |
| F2 | Décomposition des grandes instances (K-Means) | F10 | API publique + webhooks (HMAC) |
| F3 | Optimisation VRP multi-objectif | F11 | Analytics (tendances + performance) |
| F4 | Contraintes (capacité, fenêtres horaires) | F12 | Multi-dépôt |
| F5 | Export tournée (PDF / Excel) | F13 | Temps de service prédit (ML par cohorte) |
| F6 | Suivi temps réel des livraisons | F14 | Objectifs pondérés (distance / temps / carburant / CO₂) |
| F7 | Repli glouton hors-ligne (approx. haversine) | F15 | Territoires (zones + affectation livreur) |
| F8 | PWA livreur + preuve de livraison | F16 | Marque blanche (thème par entreprise) |

Sécurité & conformité : isolation multi-tenant, RBAC (403), clés API hachées SHA-256,
secrets webhook chiffrés (Fernet), rate limiting par plan, journal d'audit immuable
(loi 18-07), révocation de session (familles de refresh tokens).

Déploiement : voir [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md). API partenaire :
[`docs/API.md`](./docs/API.md) · webhooks : [`docs/WEBHOOKS.md`](./docs/WEBHOOKS.md).
Roadmap : [`docs/PRD.md`](./docs/PRD.md#3-fonctionnalités--mvp--roadmap).
