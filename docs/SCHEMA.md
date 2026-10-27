# SCHEMA — Database Schema Reference

> **Version** : 1.0.0
> **Date** : 2026-07-19
> **Auteur** : Moumen Houma
> **Portée** : PostgreSQL (source de vérité) + Redis (cache/queue/session)
> **Références** : `PRD.md` (fonctionnalités F1–F16), `ARCHITECTURE.md` §2.5 (esquisse initiale), `RULES.md` §2.4 (standards de modélisation)

Ce document est la référence normative du schéma de données. Il formalise et étend
l'esquisse de `ARCHITECTURE.md` §2.5 selon les standards définis dans `RULES.md` §2.4 :
UUID en clé primaire, `created_at`/`updated_at` systématiques, soft delete où pertinent,
contraintes `CHECK` sur les données géographiques, index composites alignés sur les
requêtes réelles (toujours filtrées par `company_id` — modèle multi-tenant).

---

## 1. Conventions

| Convention | Règle |
|---|---|
| Clé primaire | `UUID DEFAULT gen_random_uuid()` sur toutes les tables |
| Multi-tenant | Toute table métier porte `company_id` (FK indexée) — isolation stricte par entreprise |
| Horodatage | `created_at TIMESTAMPTZ DEFAULT NOW()` partout ; `updated_at` sur les entités mutables |
| Soft delete | `deleted_at TIMESTAMPTZ NULL` sur les entités éditables par l'utilisateur (véhicules, livraisons, tournées) — jamais sur les logs/historique immuables |
| Enums | `VARCHAR` + `CHECK ... IN (...)` plutôt que `CREATE TYPE ENUM`, pour permettre l'ajout de valeurs sans `ALTER TYPE` bloquant |
| Géographie | `DECIMAL(10,8)` (lat) / `DECIMAL(11,8)` (lon) + colonne `GEOGRAPHY(POINT, 4326)` générée pour les requêtes spatiales (ADR-003, PostGIS) |
| Argent | Aucun montant stocké en `FLOAT` — `DECIMAL(10,2)` uniquement |
| Fuseau horaire | `TIMESTAMPTZ` partout (l'Algérie est mono-fuseau, mais les serveurs peuvent être hors pays — cf. ARCHITECTURE §4.3 hébergement hybride) |

---

## 2. Diagramme Entité-Relation (vue d'ensemble)

```
companies ──┬──< users ──< refresh_tokens
            ├──< api_keys
            ├──< vehicles ──< routes ──< route_stops >── deliveries
            ├──< deliveries ──< delivery_status_history
            │             └──< proof_of_delivery
            ├──< optimization_jobs
            ├──< depots (Phase 2 — multi-dépôt, F12)
            └──< audit_log
```

---

## 3. Tenancy & Authentification

### 3.1 `companies`

Une entreprise cliente (flotte). Porte le plan tarifaire et ses quotas (PRD §5.1).

```sql
CREATE TABLE companies (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                    VARCHAR(255) NOT NULL,
    plan                    VARCHAR(50) NOT NULL DEFAULT 'free',
    max_vehicles            INT NOT NULL DEFAULT 1,
    max_deliveries_per_day  INT NOT NULL DEFAULT 10,
    locale                  VARCHAR(10) NOT NULL DEFAULT 'fr', -- 'fr', 'ar', 'ar-dz'
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at              TIMESTAMPTZ NULL,

    CONSTRAINT check_plan CHECK (plan IN ('free', 'starter', 'pro', 'enterprise')),
    CONSTRAINT check_locale CHECK (locale IN ('fr', 'ar', 'ar-dz'))
);

CREATE INDEX idx_companies_plan ON companies(plan) WHERE deleted_at IS NULL;
```

> Les quotas (`max_vehicles`, `max_deliveries_per_day`) sont dénormalisés ici pour un
> contrôle rapide sans jointure ; ils sont resynchronisés à chaque changement de plan
> (cf. table `plan` PRD §5.1 : Free=1/10, Starter=5/100, Pro=20/500, Enterprise=illimité → `NULL`).
> `max_vehicles`/`max_deliveries_per_day` acceptent `NULL` = illimité (Enterprise).

### 3.2 `users`

```sql
CREATE TABLE users (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id     UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    email          VARCHAR(255) NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    full_name      VARCHAR(255) NOT NULL,
    phone          VARCHAR(30),
    role           VARCHAR(50) NOT NULL DEFAULT 'manager',
    locale         VARCHAR(10) NOT NULL DEFAULT 'fr',
    active         BOOLEAN NOT NULL DEFAULT true,
    last_login_at  TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at     TIMESTAMPTZ NULL,

    CONSTRAINT check_role CHECK (role IN ('admin', 'manager', 'driver', 'viewer')),
    CONSTRAINT uq_users_email UNIQUE (email)
);

CREATE INDEX idx_users_company ON users(company_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_role ON users(company_id, role) WHERE deleted_at IS NULL;
```

Rôles RBAC (ARCHITECTURE §2.2, §5.1) :

| Rôle | Portée |
|---|---|
| `admin` | Gestion entreprise, facturation, utilisateurs |
| `manager` | Gestion flotte, import livraisons, lancement optimisation |
| `driver` | Accès à la Driver PWA (ses tournées assignées uniquement) |
| `viewer` | Lecture seule (dashboard, rapports) |

Un `driver` doit correspondre à un enregistrement `users` — le lien vers un véhicule
assigné se fait via `vehicles.driver_user_id` (§4.1), et non l'inverse, car un véhicule
peut changer de conducteur d'un jour à l'autre.

### 3.3 `refresh_tokens`

Permet la révocation des sessions (JWT access token 15 min / refresh token 7j — ARCHITECTURE §5.1).

```sql
CREATE TABLE refresh_tokens (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash   VARCHAR(255) NOT NULL, -- SHA-256 du refresh token, jamais le token en clair
    expires_at   TIMESTAMPTZ NOT NULL,
    revoked_at   TIMESTAMPTZ NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_refresh_tokens_hash UNIQUE (token_hash)
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id) WHERE revoked_at IS NULL;
```

### 3.4 `api_keys`

Clés API partenaires (F10, ARCHITECTURE §5.1 : "hash-based key sha256, scope limit").

```sql
CREATE TABLE api_keys (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id   UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name         VARCHAR(100) NOT NULL, -- label libre ("Shopify integration")
    key_hash     VARCHAR(255) NOT NULL, -- SHA-256 de la clé, jamais la clé en clair
    key_prefix   VARCHAR(12) NOT NULL,  -- 8 premiers caractères affichés à l'utilisateur (identification visuelle)
    scope        VARCHAR(20) NOT NULL DEFAULT 'read', -- read | write | admin
    last_used_at TIMESTAMPTZ,
    expires_at   TIMESTAMPTZ NULL,
    revoked_at   TIMESTAMPTZ NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT check_scope CHECK (scope IN ('read', 'write', 'admin')),
    CONSTRAINT uq_api_keys_hash UNIQUE (key_hash)
);

CREATE INDEX idx_api_keys_company ON api_keys(company_id) WHERE revoked_at IS NULL;
```

### 3.6 `webhooks`

Abonnements webhook sortants (F10). RouteOpt POST un payload JSON signé
(HMAC-SHA256 avec `secret`, en-tête `X-RouteOpt-Signature`) à chaque évènement
listé dans `events` (ex. `delivery.status_changed`, `optimization.completed`).

```sql
CREATE TABLE webhooks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id   UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    url          TEXT NOT NULL,
    secret       VARCHAR(64) NOT NULL, -- signe le payload, jamais renvoyé en clair après création
    events       VARCHAR(255) NOT NULL, -- liste d'évènements séparés par des virgules
    active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_webhooks_company ON webhooks(company_id);
```

### 3.5 `audit_log`

Journal d'audit immuable (RULES §8.1 "Insufficient Logging → audit trail" ; conformité
CNIL loi 18-07, ARCHITECTURE §5.2).

```sql
CREATE TABLE audit_log (
    id           BIGSERIAL PRIMARY KEY, -- append-only, volumineux : pas besoin d'UUID
    company_id   UUID REFERENCES companies(id) ON DELETE SET NULL,
    actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action       VARCHAR(100) NOT NULL, -- ex: 'delivery.status_changed', 'user.login', 'vehicle.deleted'
    resource_type VARCHAR(50) NOT NULL,
    resource_id  UUID,
    metadata     JSONB NOT NULL DEFAULT '{}',
    ip_address   INET,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_log_company_created ON audit_log(company_id, created_at DESC);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);
```

> Rétention : purge automatique après 1 an sauf obligation légale (ARCHITECTURE §5.2).

### 3.7 `password_reset_tokens`

Récupération de compte : lien à usage unique, valable 60 min par défaut
(`PASSWORD_RESET_EXPIRE_MINUTES`). Même discipline de stockage que §3.3 — seul le
hash est persisté, le token en clair ne circule que dans l'email.

```sql
CREATE TABLE password_reset_tokens (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash   VARCHAR(255) NOT NULL, -- SHA-256, jamais le token en clair
    expires_at   TIMESTAMPTZ NOT NULL,
    used_at      TIMESTAMPTZ NULL,      -- consommé : le lien ne fonctionne qu'une fois
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_password_reset_hash UNIQUE (token_hash)
);

CREATE INDEX ix_password_reset_tokens_user_id ON password_reset_tokens(user_id);
```

> Consommer un lien invalide **tous** les autres liens en attente de cet utilisateur et
> révoque **toutes** ses sessions (`refresh_tokens`), pas seulement la famille courante :
> un changement de mot de passe met fin à toutes les sessions.
> `POST /auth/forgot-password` répond toujours `202`, même pour une adresse inconnue
> (pas d'énumération d'utilisateurs), et est limité par IP.

---

## 4. Flotte

### 4.1 `vehicles`

```sql
CREATE TABLE vehicles (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id       UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    depot_id         UUID REFERENCES depots(id) ON DELETE SET NULL, -- NULL en MVP (mono-dépôt), voir §8
    driver_user_id   UUID REFERENCES users(id) ON DELETE SET NULL,
    name             VARCHAR(100) NOT NULL,
    vehicle_type     VARCHAR(20) NOT NULL DEFAULT 'car', -- car | van | truck | motorcycle
    license_plate    VARCHAR(20),
    capacity_weight  DECIMAL(10,2) NOT NULL DEFAULT 1000, -- kg
    capacity_volume  DECIMAL(10,2) NOT NULL DEFAULT 10,   -- m3
    depot_lat        DECIMAL(10,8) NOT NULL,
    depot_lon        DECIMAL(11,8) NOT NULL,
    depot_address    TEXT NOT NULL,
    active           BOOLEAN NOT NULL DEFAULT true,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at       TIMESTAMPTZ NULL,

    CONSTRAINT check_vehicle_type CHECK (vehicle_type IN ('car', 'van', 'truck', 'motorcycle')),
    CONSTRAINT check_capacity_weight CHECK (capacity_weight >= 0),
    CONSTRAINT check_capacity_volume CHECK (capacity_volume >= 0),
    CONSTRAINT check_depot_lat CHECK (depot_lat BETWEEN -90 AND 90),
    CONSTRAINT check_depot_lon CHECK (depot_lon BETWEEN -180 AND 180)
);

CREATE INDEX idx_vehicles_company ON vehicles(company_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_vehicles_active ON vehicles(company_id, active) WHERE deleted_at IS NULL;
```

- `vehicle_type` supporte les flottes mixtes évoquées en PRD §4.2 (voiture/camion/moto,
  contraintes de permis gérées au niveau applicatif via `driver_user_id`).
- `depot_lat`/`depot_lon`/`depot_address` restent inline (MVP mono-dépôt, cf. ARCHITECTURE
  §2.5) ; `depot_id` est prévu pour F12 (multi-dépôt, Phase 2) — voir §8.

### 4.2 `depots` (Phase 2 — F12 Multi-dépôt)

Non requis pour le MVP (un véhicule porte directement son point de départ). Introduit
quand une entreprise gère plusieurs entrepôts partagés entre véhicules.

```sql
CREATE TABLE depots (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name       VARCHAR(100) NOT NULL,
    lat        DECIMAL(10,8) NOT NULL,
    lon        DECIMAL(11,8) NOT NULL,
    address    TEXT NOT NULL,
    active     BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ NULL,

    CONSTRAINT check_depot_lat CHECK (lat BETWEEN -90 AND 90),
    CONSTRAINT check_depot_lon CHECK (lon BETWEEN -180 AND 180)
);

CREATE INDEX idx_depots_company ON depots(company_id) WHERE deleted_at IS NULL;
```

---

## 5. Livraisons

### 5.1 `deliveries`

```sql
CREATE TABLE deliveries (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id         UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    route_id           UUID REFERENCES routes(id) ON DELETE SET NULL,
    order_id           VARCHAR(100), -- référence externe (e-commerce)
    address            TEXT NOT NULL,
    address_locale     VARCHAR(10) NOT NULL DEFAULT 'fr', -- adresse saisie en 'fr' ou 'ar' (PRD §4.1)
    lat                DECIMAL(10,8),
    lon                DECIMAL(11,8),
    geocoding_status   VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending | matched | approximate | failed
    customer_phone     VARCHAR(30),
    time_window_start  TIME,
    time_window_end    TIME,
    service_time       INT NOT NULL DEFAULT 300, -- secondes
    weight             DECIMAL(10,2) NOT NULL DEFAULT 0,
    volume             DECIMAL(10,2) NOT NULL DEFAULT 0,
    priority           INT NOT NULL DEFAULT 1, -- 1=normal, 2=high, 3=urgent
    status             VARCHAR(50) NOT NULL DEFAULT 'pending',
    notes              TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at         TIMESTAMPTZ NULL,

    CONSTRAINT check_priority CHECK (priority IN (1, 2, 3)),
    CONSTRAINT check_status CHECK (status IN (
        'pending', 'geocoded', 'assigned', 'en_route', 'delivered', 'failed', 'cancelled'
    )),
    CONSTRAINT check_geocoding_status CHECK (geocoding_status IN ('pending', 'matched', 'approximate', 'failed')),
    CONSTRAINT check_lat CHECK (lat IS NULL OR lat BETWEEN -90 AND 90),
    CONSTRAINT check_lon CHECK (lon IS NULL OR lon BETWEEN -180 AND 180),
    CONSTRAINT check_weight CHECK (weight >= 0),
    CONSTRAINT check_volume CHECK (volume >= 0),
    CONSTRAINT check_time_window CHECK (
        time_window_start IS NULL OR time_window_end IS NULL OR time_window_start <= time_window_end
    )
);

CREATE INDEX idx_deliveries_company_status ON deliveries(company_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_deliveries_route ON deliveries(route_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_deliveries_order_id ON deliveries(company_id, order_id);

-- Colonne géospatiale générée pour requêtes PostGIS (clustering F15, distance approx.)
ALTER TABLE deliveries ADD COLUMN geog GEOGRAPHY(POINT, 4326)
    GENERATED ALWAYS AS (
        CASE WHEN lat IS NOT NULL AND lon IS NOT NULL
             THEN ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography
        END
    ) STORED;
CREATE INDEX idx_deliveries_geog ON deliveries USING GIST(geog);
```

- `geocoding_status` distingue "adresse résolue précisément" de "approximation acceptée"
  — nécessaire vu la couverture OSM variable et les adresses imprécises en Algérie
  (PRD §4.1, §4.3).
- `address_locale` permet de facturer/afficher l'adresse dans la langue de saisie sans
  perte d'information (support arabe/darja, PRD §4.1 ; RTL, DESIGN §6).
- `status` suit le cycle : `pending` → `geocoded` → `assigned` (affecté à une tournée)
  → `en_route` → `delivered` | `failed` ; `cancelled` à tout moment (F9 re-optimisation).

### 5.2 `delivery_status_history`

Historique append-only des changements de statut — nécessaire pour l'app livreur (F8 :
signalement "adresse introuvable", "client absent") et les analytics (F11).

```sql
CREATE TABLE delivery_status_history (
    id           BIGSERIAL PRIMARY KEY,
    delivery_id  UUID NOT NULL REFERENCES deliveries(id) ON DELETE CASCADE,
    from_status  VARCHAR(50),
    to_status    VARCHAR(50) NOT NULL,
    reason       VARCHAR(100), -- ex: 'client_absent', 'adresse_introuvable', 'fuel_shortage'
    changed_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    lat          DECIMAL(10,8), -- position du livreur au moment du changement
    lon          DECIMAL(11,8),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_delivery_status_history_delivery ON delivery_status_history(delivery_id, created_at DESC);
```

### 5.3 `proof_of_delivery`

Preuve de livraison (F8 : photo + signature).

```sql
CREATE TABLE proof_of_delivery (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    delivery_id    UUID NOT NULL REFERENCES deliveries(id) ON DELETE CASCADE,
    driver_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    photo_url      TEXT, -- MinIO/S3 (ARCHITECTURE §2.5 Files/Maps)
    signature_url  TEXT,
    lat            DECIMAL(10,8),
    lon            DECIMAL(11,8),
    captured_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_pod_delivery UNIQUE (delivery_id) -- une seule preuve par livraison
);

CREATE INDEX idx_pod_driver ON proof_of_delivery(driver_user_id);
```

---

## 6. Tournées & Optimisation

### 6.1 `routes`

```sql
CREATE TABLE routes (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id     UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    vehicle_id     UUID REFERENCES vehicles(id) ON DELETE SET NULL,
    optimization_job_id UUID REFERENCES optimization_jobs(id) ON DELETE SET NULL,
    name           VARCHAR(100),
    total_distance_m DECIMAL(10,2), -- mètres
    total_time_s   INT,             -- secondes
    geometry       JSONB,           -- GeoJSON LineString (tracé complet, non normalisable en tables)
    status         VARCHAR(50) NOT NULL DEFAULT 'planned',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    optimized_at   TIMESTAMPTZ,
    deleted_at     TIMESTAMPTZ NULL,

    CONSTRAINT check_route_status CHECK (status IN ('planned', 'dispatched', 'in_progress', 'completed', 'cancelled'))
);

CREATE INDEX idx_routes_company ON routes(company_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_routes_vehicle ON routes(vehicle_id) WHERE deleted_at IS NULL;
```

> **Écart assumé par rapport à `ARCHITECTURE.md` §2.5** : la colonne `stops JSONB` de
> l'esquisse initiale est remplacée par la table normalisée `route_stops` ci-dessous.
> Rationale (DRY, RULES §1.1) : les arrêts sont interrogés individuellement (statut,
> ETA, réordonnancement lors d'une re-optimisation dynamique F9) — un JSONB obligerait
> à réécrire tout le tableau à chaque mise à jour d'un seul arrêt. `geometry` (tracé
> GeoJSON affiché sur la carte, jamais interrogé arrêt par arrêt) reste en JSONB.

### 6.2 `route_stops`

```sql
CREATE TABLE route_stops (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    route_id         UUID NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
    delivery_id      UUID NOT NULL REFERENCES deliveries(id) ON DELETE CASCADE,
    sequence         INT NOT NULL, -- ordre de passage, 0-indexé (0 = dépôt)
    eta              TIMESTAMPTZ,
    distance_from_previous_m DECIMAL(10,2),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_route_stops_sequence UNIQUE (route_id, sequence),
    CONSTRAINT uq_route_stops_delivery UNIQUE (route_id, delivery_id)
);

CREATE INDEX idx_route_stops_route ON route_stops(route_id, sequence);
CREATE INDEX idx_route_stops_delivery ON route_stops(delivery_id);
```

### 6.3 `optimization_jobs`

```sql
CREATE TABLE optimization_jobs (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id     UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    requested_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    reoptimize_route_id UUID REFERENCES routes(id) ON DELETE SET NULL, -- F9: route re-planned in place
    trigger        VARCHAR(20) NOT NULL DEFAULT 'manual', -- manual | reoptimize | scheduled
    status         VARCHAR(50) NOT NULL DEFAULT 'pending',
    input_hash     VARCHAR(64), -- hash des paramètres d'entrée, pour cache/déduplication
    solver_strategy VARCHAR(30), -- 'or_tools' | 'greedy_fallback' (ARCHITECTURE §2.3)
    delivery_count INT,
    vehicle_count  INT,
    result         JSONB,   -- résumé de la solution (distance, temps, objective_value)
    error_message  TEXT,
    duration_ms    INT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at   TIMESTAMPTZ,

    CONSTRAINT check_job_status CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    CONSTRAINT check_job_trigger CHECK (trigger IN ('manual', 'reoptimize', 'scheduled'))
);

CREATE INDEX idx_optimization_jobs_company ON optimization_jobs(company_id, created_at DESC);
CREATE INDEX idx_optimization_jobs_status ON optimization_jobs(status);
CREATE INDEX idx_optimization_jobs_input_hash ON optimization_jobs(input_hash);
```

---

## 7. Redis — Cache, Queue & Sessions

Redis ne stocke aucune donnée de référence — c'est un cache/queue devant PostgreSQL
(ARCHITECTURE §2.5, §4.2 Cache Hierarchy L2). Toute clé doit pouvoir être régénérée
depuis PostgreSQL ou recalculée depuis OSRM.

| Usage | Key Pattern | TTL | Type Redis |
|---|---|---|---|
| Distance Matrix Cache | `dm:{coords_hash}` | 24h | `string` (JSON sérialisé) |
| Optimization Job Queue | `queue:optimize` | — | `list` (job IDs, FIFO) |
| Optimization Result Cache | `opt:result:{input_hash}` | 24h | `string` |
| Session | `session:{access_token_hash}` | 15min (aligné access token) | `hash` |
| Rate Limit | `ratelimit:{api_key_id or ip}:{window}` | 1min | `string` (compteur) |
| Geocoding Cache | `geo:{address_hash}` | 30j | `string` |
| SSE Subscribers (re-optimisation live) | `pubsub:route:{route_id}` | — | Pub/Sub channel |

---

## 8. Notes de Conception

### 8.1 Multi-dépôt (F12, Phase 2)

Le MVP garde le point de départ inline sur `vehicles` (simplicité, un seul dépôt par
entreprise dans 95% des cas pilotes). La table `depots` est définie dès maintenant
(§4.2) avec une FK nullable sur `vehicles.depot_id` pour permettre une migration sans
rupture : à l'activation de F12, un backfill copie `depot_lat/lon/address` vers un
`depots` par entreprise, puis `vehicles.depot_id` est renseigné. Les colonnes inline
restent en lecture seule après migration (compatibilité descendante des exports déjà
générés).

### 8.2 Pourquoi PostGIS n'apparaît que sur `deliveries`

ADR-003 (`ARCHITECTURE.md` §8) retient PostGIS pour les "requêtes géospatiales
natives", utilisées concrètement à un seul endroit du MVP : le clustering géographique
K-Means/DBSCAN pour la décomposition des grandes instances (> 200 livraisons,
ARCHITECTURE §4.1) et la territorialisation future (F15). Cette opération lit
`deliveries.geog`. Les dépôts et véhicules restent en `DECIMAL` simple — leur volume
est trop faible pour justifier un index GiST.

### 8.3 Ce qui reste hors schéma MVP

- **Prédiction ML du temps de service** (F13) et **optimisation multi-objectif** (F14) :
  consomment `delivery_status_history` et `optimization_jobs.result` en lecture, sans
  nouvelle table nécessaire au moment de l'entraînement offline.
- **White-label** (F16) : configuration d'apparence, pas de donnée métier — vivra dans
  `companies` sous forme d'un champ `branding JSONB` le jour où il sera implémenté.

---

## 9. Phase 4 — Monétisation & Terrain (F17–F20)

### 9.1 `cod_payments` (F17 — paiement à la livraison)

Un enregistrement de rapprochement par livraison encaissée. Migration `0013`.

| Colonne | Type | Notes |
|---------|------|-------|
| `id` | UUID PK | |
| `company_id` | UUID FK→companies | CASCADE, isolation tenant |
| `delivery_id` | UUID FK→deliveries | CASCADE ; **UNIQUE** (un rapprochement par livraison) |
| `route_id` | UUID FK→routes | SET NULL |
| `driver_user_id` | UUID FK→users | SET NULL |
| `amount_expected` | Numeric(12,2) | copié de `deliveries.cod_amount` à l'encaissement |
| `amount_collected` | Numeric(12,2) | espèce réellement collectée |
| `currency` | String(3) | défaut `DZD` |
| `method` | String(20) | `cash` \| `baridimob` \| `ccp` \| `none` |
| `status` | String(20) | `pending` \| `collected` \| `reconciled` \| `discrepancy` |
| `collected_at` | timestamptz | |

Colonnes ajoutées à `deliveries` (migration `0013`) : `cod_amount Numeric(12,2)` (total
dû à l'arrêt, saisi à l'import ; NULL = prépayé), `cod_currency String(3)` défaut `DZD`.

### 9.2 `subscriptions` + `invoices` (F19 — facturation SaaS)

Migration `0014`. `subscriptions` : une ligne active par company reflétant la formule
facturée (`plan`, `status` active|canceled, `amount_da`, `started_at`, `canceled_at`) ;
le changement de formule clôt l'ancienne et en ouvre une nouvelle (historique). `invoices` :
une charge par période `YYYY-MM` (`period` UNIQUE par company, `plan`, `amount_da`,
`status` pending|paid|void, `method` cash|ccp|baridimob|stripe, `reference`, `issued_at`,
`paid_at`). Montants en DZD (PRD §5.1). Les plafonds de formule vivent sur `companies`
(`max_vehicles`, `max_deliveries_per_day`) et sont l'autorité pour l'application des quotas.

### 9.3 `fuel_stations` + colonnes carburant véhicule (F20)

Migration `0015`. `fuel_stations` (company-scoped, soft-delete) : `name`, `lat`/`lon`,
`fuel_types` (CSV : essence,diesel,gpl,electric), `status` available|shortage|closed,
`notes`. Colonnes ajoutées à `vehicles` : `fuel_range_km Numeric(8,2)` (NULL = illimité ;
alimente la contrainte d'autonomie OR-Tools) et `fuel_type String(20)`
(essence|diesel|gpl|electric).

---

*Schéma versionné via migrations séquentielles (Alembic). Toute modification de ce
document doit être accompagnée d'une migration correspondante dans `migrations/`.*
