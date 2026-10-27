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

# Email transactionnel (réinitialisation de mot de passe)
# noop (silencieux) | log (écrit le lien dans les logs) | smtp (envoi réel).
# Défaut `log` : sans relais SMTP, le lien de réinitialisation reste récupérable
# dans les logs du backend. En production, préférez `smtp`.
EMAIL_PROVIDER=smtp
EMAIL_FROM=no-reply@routeopt.dz
SMTP_HOST=smtp.votre-relais
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_USE_TLS=true
# PUBLIC_BASE_URL sert aussi à construire les liens de réinitialisation.
PUBLIC_BASE_URL=https://app.routeopt.dz
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

Placez-les dans `infra/secrets/` (git-ignoré) ; l'override de production les
monte comme secrets Docker aux chemins pointés par `JWT_PRIVATE_KEY_PATH` /
`JWT_PUBLIC_KEY_PATH` (`/run/secrets/jwt_private_key` / `_public_key`). Backend
et worker n'ont besoin que de ces deux fichiers pour l'auth (le worker n'émet
pas de jeton).

## 3. Base de données & migrations

Provisionnez PostgreSQL **avec PostGIS** (colonne `deliveries.geog`). Appliquez
les migrations au déploiement, avant de démarrer l'API :

```bash
cd backend && alembic upgrade head
```

Vérifiez au préalable le SQL généré d'une nouvelle migration :
`alembic upgrade <rev_précédente>:<rev> --sql`.

### 3.1 Données de démonstration (optionnel)

Pour qu'une instance fraîche soit **cliquable** plutôt qu'un écran vide (démos
prospects, environnement de test), un script sème une société de démo :

```bash
cd backend && python scripts/seed_demo.py
```

Il est **idempotent** (rejouable sans doublon) et crée : société « Démo RouteOpt »
(formule `pro`), un gérant `demo@routeopt.dz` / `demo-pass-123`, un livreur
`driver@routeopt.dz` / `driver-pass-123`, un dépôt Alger, 3 véhicules et ~15
livraisons Alger (dont quelques-unes en paiement à la livraison). Il tente ensuite
une optimisation : **lancez-le une fois la pile en bonne santé** (worker + OSRM up),
sinon il sème les données et vous invite à optimiser depuis l'interface.
À ne **pas** exécuter sur une base contenant de vrais clients.

## 4. Build & lancement

Chaque composant a un `Dockerfile`. L'override de production
[`docker-compose.prod.yml`](../docker-compose.prod.yml) part de
`docker-compose.yml` et :

- écarte postgres/redis/minio (parqués sous un profil non activé — services managés) ;
- force `ENVIRONMENT=production`, `DEBUG=false`, `LOG_LEVEL=INFO` ;
- monte les clés JWT comme *secrets* Docker (`./infra/secrets/jwt-*.pem` → `/run/secrets/*`) ;
- retire les ports publics de l'API/front (exposés seulement à la passerelle) ;
- réplique backend + worker (×2) avec `restart: unless-stopped` ;
- ajoute un service `gateway` nginx (TLS + proxy, §5).

```bash
cp .env.prod.example .env          # puis renseigner les vraies valeurs / secrets
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Le frontend se build en statique (`npm run build` → `dist/`) et se sert derrière
un CDN ou nginx (voir `infra/`), avec `VITE_API_BASE_URL` pointant sur l'API.

## 5. Passerelle & TLS

Le service `gateway` s'appuie sur [`infra/nginx/`](../infra/nginx) :

- [`nginx.conf`](../infra/nginx/nginx.conf) — upstreams `backend:8000` / `frontend:5173`, limite d'upload 12 Mo (photos POD) ;
- [`conf.d/routeopt.conf`](../infra/nginx/conf.d/routeopt.conf) — redirection HTTP→HTTPS, terminaison TLS, `/api/` → backend, reste → front.

À faire côté hôte :

- déposer les certificats dans `infra/nginx/certs/` (`fullchain.pem`, `privkey.pem` — ex. Let's Encrypt ; répertoire git-ignoré) ;
- remplacer `server_name app.routeopt.dz` par votre domaine ;
- `/api/` transmet `X-Forwarded-For` (indispensable au journal d'audit) et applique HSTS + en-têtes de sécurité.

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

## 8. Déploiement sur un VPS (un seul hôte)

Cible réaliste : un VPS Ubuntu **8–16 Go de RAM** — c'est l'OSRM Algérie qui fixe
le plancher mémoire (§ contraintes techniques du PRD). Prérequis one-off sur l'hôte :
Docker + plugin Compose, un `.env` renseigné (à partir de `.env.prod.example`),
les clés JWT dans `infra/secrets/`, les certificats TLS dans `infra/nginx/certs/`,
et les données OSRM construites une fois (`infra/osrm/prepare.sh`).

DNS : faites pointer `app.routeopt.dz` (application) et `routeopt.dz` /
`www.routeopt.dz` (vitrine) vers l'IP du VPS. Certificats via **Let's Encrypt** —
l'emplacement `/.well-known/acme-challenge/` est déjà prévu dans
`conf.d/routeopt.conf` (mode webroot `certbot`), puis déposez `fullchain.pem` /
`privkey.pem` dans `infra/nginx/certs/`.

Le déploiement lui-même est scripté — [`infra/deploy.sh`](../infra/deploy.sh)
(fetch → build → `alembic upgrade head` dans un conteneur jetable → `up -d` →
attente de `/health/ready`) :

```bash
./infra/deploy.sh                    # déploie la branche courante
```

Le script est idempotent (rejouable pour une mise à jour). Optionnel ensuite :
`python backend/scripts/seed_demo.py` pour une société de démo cliquable (§3.1) —
jamais sur une base contenant de vrais clients.

## 9. Sauvegardes & restauration

[`infra/backup.sh`](../infra/backup.sh) fait un `pg_dump` compressé et, si les
variables `S3_*` sont présentes, le pousse vers le bucket. À planifier par cron :

```cron
0 2 * * *  /opt/routeopt/infra/backup.sh >> /var/log/routeopt-backup.log 2>&1
```

**Une sauvegarde jamais restaurée n'est pas une sauvegarde.** Testez une
restauration périodiquement sur une base jetable :

```bash
gunzip -c routeopt-<stamp>.sql.gz | psql "postgresql://user:pass@host:5432/routeopt_restore_test"
```

## 10. Démo temporaire sans VPS (tunnel)

Pour montrer une instance en direct **avant** d'avoir un VPS et un domaine,
[`infra/demo-tunnel.sh`](../infra/demo-tunnel.sh) ouvre un tunnel Cloudflare
temporaire (sans compte, sans DNS) vers la pile locale :

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
./infra/demo-tunnel.sh 80            # tunnel vers la passerelle
```

L'URL `*.trycloudflare.com` produite est **éphémère** : elle change à chaque
lancement et meurt à l'arrêt. Elle sert à une démo en direct que vous pilotez —
**à ne pas mettre dans un email froid**. Pour que la SPA joigne son API à travers
le tunnel, buildez le frontend avec `VITE_API_BASE_URL` **vide** (appel same-origin
`/api`) et alignez `ALLOWED_ORIGINS` / `PUBLIC_BASE_URL` sur l'hôte du tunnel.
Pour une adresse stable, utilisez un tunnel nommé avec votre propre domaine.
