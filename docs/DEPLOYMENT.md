# Déploiement

Guide de mise en production de RouteOpt. Pour le développement local, voir le
[README](../README.md#démarrage-rapide-local).

## Vue d'ensemble

| Service | Rôle | Externalisable |
|---|---|---|
| `backend` | API FastAPI (Auth, Orders, Fleet, Routes, API publique) | — |
| `optimization-worker` | Résolution VRP (consomme `queue:optimize`) | — |
| `frontend` | Web app + Driver PWA (build statique servi par nginx/CDN) | — |
| PostgreSQL + PostGIS | Source de vérité | ✅ (RDS/Cloud SQL managé) |
| Redis | Cache, file d'attente, sessions | ✅ (ElastiCache/Memorystore) |
| MinIO / S3 | Preuves de livraison, exports | ✅ (S3 managé) |
| OSRM | Moteur de routage | ✅ (instance dédiée, voir `infra/osrm`) |

Backend et worker partagent la même image de base et la même config ; ils
diffèrent par la commande de démarrage (`uvicorn` vs `python -m optimizer.worker`).

## 1. Prérequis secrets & configuration

La configuration est chargée depuis l'environnement ([`backend/src/routeopt/config.py`](../backend/src/routeopt/config.py)).
Un **garde-fou de production** rejette au démarrage toute valeur par défaut
non sûre dès que `ENVIRONMENT != "local"` :

- `DEBUG` doit être `false`
- `SECRET_KEY` ne doit pas être le défaut de dev
- les identifiants S3 ne doivent pas être `minioadmin`
- `ALLOWED_ORIGINS` ne doit pas contenir `localhost` / `127.0.0.1`

Variables clés à définir :

```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

DB_URL=postgresql+asyncpg://<user>:<pass>@<host>:5432/routeopt
REDIS_URL=redis://<host>:6379/0

# Object storage (S3 managé ou MinIO)
S3_ENDPOINT=https://s3.<region>.amazonaws.com
S3_ACCESS_KEY=<clé>
S3_SECRET_KEY=<secret>
S3_BUCKET=routeopt-prod

# Auth JWT (RS256) — voir §2
JWT_PRIVATE_KEY_PATH=/run/secrets/jwt-private.pem
JWT_PUBLIC_KEY_PATH=/run/secrets/jwt-public.pem

# Dérive les clés de chiffrement au repos (secrets webhook). 32+ octets aléatoires.
SECRET_KEY=<openssl rand -hex 32>

# Front autorisé
ALLOWED_ORIGINS=["https://app.routeopt.dz"]

# Routage
OSRM_URL=http://osrm:5000
NOMINATIM_URL=https://nominatim.votre-hote   # une instance self-hosted lève la limite ~1 req/s
NOMINATIM_RATE_LIMIT_S=0

# Observabilité (optionnel)
SENTRY_DSN=https://...ingest.sentry.io/...
```

Stockez les secrets dans un gestionnaire (Docker/Kubernetes secrets, AWS Secrets
Manager, Vault) — **jamais** dans l'image ni le dépôt.

## 2. Bootstrap des clés JWT (RS256)

Les jetons sont signés en RS256. Générez une paire de clés **une fois** et
montez-la comme secret (le dossier `backend/keys/` est git-ignoré) :

```bash
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out jwt-private.pem
openssl rsa -in jwt-private.pem -pubout -out jwt-public.pem
```

Montez `jwt-private.pem` / `jwt-public.pem` aux chemins pointés par
`JWT_PRIVATE_KEY_PATH` / `JWT_PUBLIC_KEY_PATH`. Backend et worker n'ont besoin
que de ces deux fichiers pour l'auth (le worker n'émet pas de jeton).

## 3. Base de données & migrations

Provisionnez PostgreSQL **avec PostGIS** (colonne `deliveries.geog`). Appliquez
les migrations au déploiement, avant de démarrer l'API :

```bash
cd backend && alembic upgrade head
```

Vérifiez au préalable le SQL généré d'une nouvelle migration :
`alembic upgrade <rev_précédente>:<rev> --sql`.

## 4. Build & lancement

Chaque composant a un `Dockerfile`. En s'appuyant sur `docker-compose.yml`
comme base, un override de production (`docker-compose.prod.yml`) :

- retire les services managés en externe (postgres/redis/minio) ;
- injecte les variables ci-dessus et les secrets JWT ;
- fixe `restart: unless-stopped` et des `healthcheck` ;
- fait tourner plusieurs workers `optimization-worker` selon la charge.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Le frontend se build en statique (`npm run build` → `dist/`) et se sert derrière
un CDN ou nginx (voir `infra/`), avec `VITE_API_BASE_URL` pointant sur l'API.

## 5. Passerelle & TLS

Placez un reverse proxy (nginx, `infra/nginx`) devant l'API et le front :

- terminaison TLS (certificats gérés, ex. Let's Encrypt) ;
- transfert vers `backend:8000` et service des assets front ;
- transmission de `X-Forwarded-For` (utilisé par le journal d'audit) ;
- en-têtes de sécurité (HSTS, CSP).

## 6. Santé & observabilité

- **Liveness** : `GET /health` — le process répond.
- **Readiness** : `GET /health/ready` — connectivité database / redis / osrm
  (`503` si database ou redis sont indisponibles ; OSRM non fatal → repli haversine).
- **Erreurs** : Sentry s'initialise automatiquement quand `SENTRY_DSN` est défini.
- **Audit** : les actions sensibles alimentent `audit_log` (voir `GET /api/v1/audit-log`, admin).

## 7. Checklist post-déploiement

- [ ] `GET /health/ready` renvoie `200` (database + redis `ok`).
- [ ] `alembic current` est à `head`.
- [ ] Un cycle register → login → optimize aboutit à une tournée.
- [ ] Le worker consomme `queue:optimize` (logs `job … -> completed`).
- [ ] OSRM joignable (sinon résultats `is_suboptimal`, à surveiller).
- [ ] Sauvegardes PostgreSQL + rétention `audit_log` (purge > 1 an, loi 18-07).
