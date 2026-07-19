# ARCHITECTURE — RouteOpt System Architecture

> **Version** : 1.0.0  
> **Date** : 2026-07-19  
> **Architecte** : Moumen Houma  
> **Paradigme** : Microservices légers + Event-Driven + Optimisation as a Service

---

## 1. Vue d'Ensemble (High-Level)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   Web App    │  │  Driver PWA  │  │  Admin Panel │  │  Partner API    │  │
│  │  (React/Vue) │  │  (React/Vue) │  │  (React/Vue) │  │  (REST/GraphQL) │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘  │
└─────────┼─────────────────┼─────────────────┼───────────────────┼───────────┘
          │                 │                 │                   │
          └─────────────────┴─────────────────┴───────────────────┘
                                    │
                          ┌─────────┴─────────┐
                          │   API Gateway     │
                          │  (Kong / Nginx)   │
                          │  Rate Limiting    │
                          │  Auth (JWT)       │
                          └─────────┬─────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
┌─────────┴─────────┐   ┌───────────┴───────────┐   ┌─────────┴─────────┐
│   CORE SERVICES   │   │   OPTIMIZATION ENGINE   │   │   DATA LAYER      │
│                   │   │                         │   │                   │
│ ┌───────────────┐ │   │ ┌─────────────────────┐ │   │ ┌───────────────┐ │
│ │ Order Service │ │   │ │ Optimization Worker │ │   │ │ PostgreSQL    │ │
│ │ (Node/FastAPI)│ │   │ │ (Python + OR-Tools) │ │   │ │ (Main DB)     │ │
│ └───────────────┘ │   │ │                     │ │   │ └───────────────┘ │
│ ┌───────────────┐ │   │ │ - VRP Solver        │ │   │ ┌───────────────┐ │
│ │ Fleet Service │ │   │ │ - Distance Matrix   │ │   │ │ Redis         │ │
│ │ (Node/FastAPI)│ │   │ │   (OSRM)            │ │   │ │ (Cache/Queue) │ │
│ └───────────────┘ │   │ │ - Warm-start        │ │   │ └───────────────┘ │
│ ┌───────────────┐ │   │ │ - Fallback greedy   │ │   │ ┌───────────────┐ │
│ │ Route Service │ │   │ └─────────────────────┘ │   │ │ MinIO/S3      │ │
│ │ (Node/FastAPI)│ │   │                         │   │ │ (Files/Maps)  │ │
│ └───────────────┘ │   │ ┌─────────────────────┐ │   │ └───────────────┘ │
│ ┌───────────────┐ │   │ │ OSRM Instance       │ │   │                   │
│ │ Auth Service  │ │   │ │ (C++ Self-Hosted)   │ │   │                   │
│ │ (Node/FastAPI)│ │   │ │ - Algeria OSM data  │ │   │                   │
│ └───────────────┘ │   │ │ - CH/MLD profiles   │ │   │                   │
│                   │   │ └─────────────────────┘ │   │                   │
└───────────────────┘   └───────────────────────┘   └───────────────────┘
          │                         │                         │
          └─────────────────────────┴─────────────────────────┘
                                    │
                          ┌─────────┴─────────┐
                          │   Message Queue   │
                          │   (Redis/RabbitMQ)│
                          │                   │
                          │ - optimize.job    │
                          │ - route.updated   │
                          │ - driver.assigned │
                          └───────────────────┘
```

---

## 2. Composants Détaillés

### 2.1 API Gateway
- **Kong** ou **Nginx** avec modules Lua
- **Rate limiting** : 100 req/min par clé API (Starter), 1000 req/min (Pro)
- **Authentication** : JWT (access token 15min, refresh token 7j)
- **CORS** : Origines contrôlées (web app, PWA, partenaires)
- **SSL/TLS** : Let's Encrypt auto-renew

### 2.2 Core Services (REST API)

#### Order Service (Node.js / FastAPI)
```
POST /api/v1/orders/bulk          → Import CSV/Excel livraisons
GET  /api/v1/orders/{id}          → Détails livraison
PUT  /api/v1/orders/{id}/status   → Mise à jour statut (livré, échec, etc.)
DELETE /api/v1/orders/{id}        → Annulation
```
- **Responsabilité** : CRUD livraisons, validation données, géocodage
- **Géocodage** : Nominatim OSM (self-hosted ou public avec cache agressif)
- **Validation** : Schema JSON, fenêtres horaires cohérentes, coordonnées valides

#### Fleet Service (Node.js / FastAPI)
```
POST /api/v1/fleets               → Création flotte
GET  /api/v1/fleets/{id}/vehicles → Liste véhicules
POST /api/v1/fleets/{id}/vehicles → Ajout véhicule (capacité, dépôt)
PUT  /api/v1/vehicles/{id}        → Modification véhicule
```
- **Responsabilité** : Gestion flottes, véhicules, dépôts, contraintes capacités

#### Route Service (Node.js / FastAPI)
```
POST /api/v1/routes/optimize      → Lancer optimisation
GET  /api/v1/routes/{id}          → Récupérer tournée optimisée
GET  /api/v1/routes/{id}/export   → Export PDF/Excel/GPX
POST /api/v1/routes/{id}/reoptimize → Re-optimisation dynamique
```
- **Responsabilité** : Orchestration optimisation, stockage résultats, export
- **Async** : L'optimisation est asynchrone (job queue), retourne immédiatement un job ID

#### Auth Service (Node.js / FastAPI)
```
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/forgot-password
```
- **Responsabilité** : Authentification, autorisation RBAC, gestion clés API
- **RBAC** : admin, manager, driver, viewer

### 2.3 Optimization Engine (Python)

#### Architecture du Solver

```
┌─────────────────────────────────────────────────────────────┐
│              Optimization Worker (Python)                   │
│                                                             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐  │
│  │  Preprocessor│   │   Solver    │   │  Postprocessor  │  │
│  │             │   │             │   │                 │  │
│  │ - Validate  │   │ - OR-Tools  │   │ - Format output │  │
│  │ - Geocode   │   │   CP-SAT    │   │ - Compute stats │  │
│  │ - Build     │   │ - Meta-     │   │ - Cache result  │  │
│  │   distance  │   │   heuristics│   │ - Notify        │  │
│  │   matrix    │   │ - Time limit│   │   subscribers   │  │
│  │             │   │   (config)  │   │                 │  │
│  └─────────────┘   └─────────────┘   └─────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Distance Matrix Builder                 │   │
│  │                                                      │   │
│  │  IF cached(matrix_key):                              │   │
│  │      RETURN cache                                    │   │
│  │  ELSE:                                               │   │
│  │      coords = [(lat,lon) for each stop]             │   │
│  │      matrix = OSRM.table(coords)  # NxN              │   │
│  │      cache(matrix, TTL=24h)                          │   │
│  │      RETURN matrix                                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Fallback Strategy                     │   │
│  │                                                      │   │
│  │  IF OR-Tools timeout (> 30s):                        │   │
│  │      -> Decomposition géographique (clustering)     │   │
│  │      -> Solve sub-problems                            │   │
│  │  IF OR-Tools infeasible:                             │   │
│  │      -> Greedy nearest-neighbor + local search        │   │
│  │      -> Flag "solution sub-optimale"                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

#### OR-Tools Configuration

```python
# Solver configuration for production
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

def configure_solver():
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()

    # First solution heuristic: PATH_CHEAPEST_ARC (fast, good initial solution)
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    # Metaheuristic: GUIDED_LOCAL_SEARCH (best balance quality/time)
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )

    # Time limit: 30s for < 50 stops, 120s for < 200 stops, 300s for > 200
    search_parameters.time_limit.seconds = 30

    # Log progress (dev only)
    search_parameters.log_search = False

    return search_parameters
```

#### Dimensions OR-Tools Utilisées

| Dimension | Type | Contrainte | Description |
|-----------|------|------------|-------------|
| **Distance** | Transit | Minimiser | Distance totale parcourue (km) |
| **Time** | Transit + Slack | Fenêtres horaires | Temps cumulé incluant service + attente |
| **Capacity** | Unary | Capacité véhicule | Poids ou volume total par véhicule |
| **VehicleCount** | Penalty | Minimiser | Pénalité par véhicule utilisé (optionnel) |

### 2.4 OSRM — Routing Engine

#### Déploiement

```yaml
# docker-compose.yml (simplified)
version: '3.8'
services:
  osrm:
    image: osrm/osrm-backend:latest
    command: >
      osrm-routed
      /data/algeria.osrm
      --algorithm mld
      --max-table-size 10000
    volumes:
      - ./osrm-data:/data
    ports:
      - "5000:5000"
    deploy:
      resources:
        limits:
          memory: 16G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/table/v1/driving/0,0;1,1"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### Prétraitement OSM Algérie

```bash
# 1. Télécharger les données OSM Algérie
wget https://download.geofabrik.de/africa/algeria-latest.osm.pbf

# 2. Extraction (profile voiture)
docker run -t -v $(pwd):/data osrm/osrm-backend:latest \
  osrm-extract /data/algeria-latest.osm.pbf \
  -p /opt/car.lua

# 3. Partition (MLD)
docker run -t -v $(pwd):/data osrm/osrm-backend:latest \
  osrm-partition /data/algeria-latest.osrm

# 4. Customization
docker run -t -v $(pwd):/data osrm/osrm-backend:latest \
  osrm-customize /data/algeria-latest.osrm
```

**Ressources requises** : ~8–16 GB RAM, ~2–4 GB disque pour l'Algérie.

### 2.5 Data Layer

#### PostgreSQL Schema (Simplifié)

> Voir `SCHEMA.md` pour le schéma complet et détaillé (contraintes, index, historique, conformité).

```sql
-- Core tables
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'manager',
    company_id UUID REFERENCES companies(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    plan VARCHAR(50) DEFAULT 'free',
    max_vehicles INT DEFAULT 1,
    max_deliveries_per_day INT DEFAULT 10,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE vehicles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    name VARCHAR(100) NOT NULL,
    capacity_weight DECIMAL(10,2) DEFAULT 1000, -- kg
    capacity_volume DECIMAL(10,2) DEFAULT 10,     -- m3
    depot_lat DECIMAL(10,8),
    depot_lon DECIMAL(11,8),
    depot_address TEXT,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    order_id VARCHAR(100),
    address TEXT NOT NULL,
    lat DECIMAL(10,8),
    lon DECIMAL(11,8),
    time_window_start TIME,
    time_window_end TIME,
    service_time INT DEFAULT 300, -- seconds
    weight DECIMAL(10,2) DEFAULT 0,
    volume DECIMAL(10,2) DEFAULT 0,
    priority INT DEFAULT 1, -- 1=normal, 2=high, 3=urgent
    status VARCHAR(50) DEFAULT 'pending',
    route_id UUID REFERENCES routes(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    name VARCHAR(100),
    vehicle_id UUID REFERENCES vehicles(id),
    total_distance DECIMAL(10,2), -- meters
    total_time INT, -- seconds
    stops JSONB, -- array of {delivery_id, sequence, eta}
    geometry JSONB, -- GeoJSON LineString
    status VARCHAR(50) DEFAULT 'planned',
    created_at TIMESTAMP DEFAULT NOW(),
    optimized_at TIMESTAMP
);

CREATE TABLE optimization_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, completed, failed
    input_hash VARCHAR(64), -- hash of input for cache
    result JSONB,
    error_message TEXT,
    duration_ms INT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_deliveries_company ON deliveries(company_id);
CREATE INDEX idx_deliveries_route ON deliveries(route_id);
CREATE INDEX idx_routes_company ON routes(company_id);
CREATE INDEX idx_optimization_jobs_company ON optimization_jobs(company_id);
CREATE INDEX idx_optimization_jobs_status ON optimization_jobs(status);
```

#### Redis Usage

| Usage | Key Pattern | TTL | Description |
|-------|------------|-----|-------------|
| Distance Matrix Cache | `dm:{hash}` | 24h | Cache matrices OSRM |
| Job Queue | `queue:optimize` | — | File d'attente optimisation |
| Session | `session:{token}` | 7j | Sessions utilisateurs |
| Rate Limit | `ratelimit:{ip}` | 1min | Compteur requêtes |
| Geocoding Cache | `geo:{address_hash}` | 30j | Cache résultats géocodage |

---

## 3. Flux de Données (Data Flow)

### 3.1 Optimisation d'une Tournée (Happy Path)

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Manager │     │  Web App     │     │  Route Svc   │     │  Redis Queue │
│ (Upload) │────▶│  (React)     │────▶│  (FastAPI)   │────▶│  (optimize)  │
└──────────┘     └──────────────┘     └──────────────┘     └──────┬───────┘
                                                                  │
                                                                  │ Pop
                                                                  ▼
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Manager │◀────│  Web App     │◀────│  Route Svc   │◀────│  Opt Worker  │
│ (Result) │     │  (Polling)   │     │  (SSE/WS)    │     │  (Python)    │
└──────────┘     └──────────────┘     └──────────────┘     └──────┬───────┘
                                                                  │
                    ┌─────────────────────────────────────────────┘
                    │
                    ▼
          ┌─────────────────┐     ┌─────────────────┐
          │   OSRM (C++)    │     │   PostgreSQL    │
          │  (Distance      │     │  (Store result) │
          │   Matrix)       │     │                 │
          └─────────────────┘     └─────────────────┘
```

### 3.2 Re-optimisation Dynamique (Livraison annulée)

```
Driver App ──▶ Route Svc ──▶ Redis Queue ──▶ Opt Worker
     │              │              │              │
     │              │              │              │
     │              │              │              ├──▶ Fetch current state
     │              │              │              ├──▶ Remove cancelled stop
     │              │              │              ├──▶ Re-solve (warm-start)
     │              │              │              └──▶ Push new route to driver
     │              │              │
     │              │◀────────────┘
     │              │ (SSE push)
     │◀─────────────┘
     │ (New route + ETA)
```

---

## 4. Scalability & Performance

### 4.1 Décomposition pour Grandes Instances

Pour > 200 livraisons, décomposition en 2 phases :

```
Phase 1: Clustering (K-Means / DBSCAN géographique)
    ┌─────────────────────────────────────────┐
    │          Zone Alger Centre              │
    │    ┌─────┐  ┌─────┐  ┌─────┐          │
    │    │ C1  │  │ C2  │  │ C3  │          │
    │    │(50) │  │(45) │  │(60) │          │
    │    └─────┘  └─────┘  └─────┘          │
    │         ┌─────┐  ┌─────┐              │
    │         │ C4  │  │ C5  │              │
    │         │(30) │  │(35) │              │
    │         └─────┘  └─────┘              │
    └─────────────────────────────────────────┘

Phase 2: VRP par cluster (OR-Tools, < 100 stops chacun)
    -> Parallel solving -> Merge -> Global refinement
```

### 4.2 Caching Strategy

```
┌─────────────────────────────────────────────────────────────┐
│                    Cache Hierarchy                          │
│                                                             │
│  L1: In-memory (Python dict)                                │
│      -> Distance matrix pour session active                  │
│      -> TTL: durée de la requête                             │
│                                                             │
│  L2: Redis                                                  │
│      -> Distance matrix par hash de coordonnées              │
│      -> Résultats optimisation par hash d'input              │
│      -> TTL: 24h                                             │
│                                                             │
│  L3: PostgreSQL                                             │
│      -> Historique complet des optimisations                 │
│      -> Warm-start: réutiliser solution précédente           │
│                                                             │
│  L4: OSRM (recompute)                                       │
│      -> Dernier recours, toujours < 5ms                      │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Infrastructure Scaling

| Charge | Configuration | Coût estimé/mois |
|--------|--------------|------------------|
| **Développement** | 1 VPS (4 vCPU, 8 GB RAM) + OSRM | ~50 EUR |
| **MVP (5 flottes)** | 2 VPS (4 vCPU, 16 GB RAM) + OSRM + PostgreSQL | ~150 EUR |
| **Croissance (50 flottes)** | 3 VPS app + 1 VPS OSRM + Managed PostgreSQL | ~500 EUR |
| **Scale (500 flottes)** | Kubernetes (GKE/EKS) + OSRM cluster + Redis Cluster | ~2000 EUR |

---

## 5. Sécurité

### 5.1 Authentification & Autorisation

```
┌─────────────────────────────────────────────────────────────┐
│                    Auth Flow (JWT)                          │
│                                                             │
│  1. Login -> Auth Service                                    │
│     -> Verify credentials (bcrypt)                           │
│     -> Generate access_token (15min) + refresh_token (7j)  │
│                                                             │
│  2. API Request -> API Gateway                               │
│     -> Validate JWT signature (RS256)                        │
│     -> Extract claims (user_id, company_id, role)            │
│     -> Forward to service with X-User-ID header              │
│                                                             │
│  3. Service Level                                             │
│     -> Verify company_id matches resource                    │
│     -> RBAC check (admin/manager/driver/viewer)            │
│                                                             │
│  4. API Keys (partenaires)                                  │
│     -> Hash-based key (sha256)                             │
│     -> Rate limit per key                                    │
│     -> Scope limit (read-only, write, admin)               │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Data Protection (CNIL Algérie — Loi 18-07)

- **Encryption at rest** : PostgreSQL avec pgcrypto, fichiers MinIO avec SSE-S3
- **Encryption in transit** : TLS 1.3 pour toutes les communications
- **PII minimization** : Adresses stockées, mais pas de noms complets des clients finaux (seulement ID commande)
- **Retention** : Données de livraison archivées après 90j, suppression complète après 1 an (sauf obligation légale)
- **Consentement** : Opt-in explicite pour tracking GPS des livreurs

---

## 6. Monitoring & Observability

### 6.1 Métriques Clés (Prometheus + Grafana)

| Métrique | Type | Seuil d'alerte |
|----------|------|---------------|
| `optimization_duration_seconds` | Histogram | P99 > 30s |
| `optimization_requests_total` | Counter | — |
| `osrm_response_time_ms` | Histogram | P99 > 100ms |
| `osrm_cache_hit_rate` | Gauge | < 80% |
| `api_requests_per_second` | Gauge | > 1000/s |
| `api_error_rate` | Gauge | > 1% |
| `queue_depth` | Gauge | > 100 jobs |
| `db_connection_pool_usage` | Gauge | > 80% |

### 6.2 Logging (ELK Stack ou Loki)

```json
{
  "timestamp": "2026-07-19T10:30:00Z",
  "level": "INFO",
  "service": "optimization-worker",
  "trace_id": "abc123",
  "event": "optimization_completed",
  "company_id": "uuid",
  "stops": 45,
  "vehicles": 3,
  "duration_ms": 4200,
  "total_distance_km": 127.5,
  "objective_value": 127500
}
```

---

## 7. Déploiement

### 7.1 Environnements

| Environnement | Infra | Données | Usage |
|---------------|-------|---------|-------|
| **Local** | Docker Compose | Seed data | Développement |
| **Staging** | VPS cloud | Anonymized prod | Tests, démo |
| **Production** | VPS cloud / K8s | Données réelles | Live |

### 7.2 CI/CD Pipeline

```
Git Push ──▶ GitHub Actions ──▶ Build & Test ──▶ Docker Build ──▶ Push Registry
                                                          │
                                                          ▼
                                              ┌─────────────────────┐
                                              │   Staging Deploy    │
                                              │   (Smoke Tests)     │
                                              └──────────┬──────────┘
                                                         │
                                                         ▼
                                              ┌─────────────────────┐
                                              │   Production Deploy │
                                              │   (Blue/Green)      │
                                              └─────────────────────┘
```

---

## 8. Décisions Architecturales (ADRs)

### ADR-001 : OR-Tools vs Solver Commercial
**Décision** : OR-Tools (Google) open-source  
**Rationale** : Gratuit, performant (0.02s pour 17 nœuds), communauté active, pas de lock-in vendor. Alternative (Gurobi/CPLEX) coûte 10 000+ EUR/an.  
**Conséquence** : Nécessite expertise interne en optimisation combinatoire.

### ADR-002 : OSRM vs API Commerciale (Google Maps, HERE)
**Décision** : OSRM self-hosted  
**Rationale** : Gratuit, données OSM pour l'Algérie suffisantes, pas de dépendance API externe, latence < 5ms.  
**Conséquence** : RAM élevée (16 GB), maintenance des données OSM, pas de trafic temps réel.

### ADR-003 : PostgreSQL vs MongoDB
**Décision** : PostgreSQL avec PostGIS  
**Rationale** : Données relationnelles fortement structurées, requêtes géospatiales natives, ACID pour transactions financières.  
**Conséquence** : Scaling horizontal plus complexe que NoSQL (mitigé par sharding si nécessaire).

### ADR-004 : Microservices vs Monolith
**Décision** : Services modulaires mais déployables ensemble (modular monolith)  
**Rationale** : Équipe de 1–3 développeurs, complexité ops réduite, possibilité d'extraire en microservices plus tard.  
**Conséquence** : Déploiement atomique, mais scalabilité limitée par service.

---

*Architecture documentée selon les standards C4 Model (Level 1–3).*
