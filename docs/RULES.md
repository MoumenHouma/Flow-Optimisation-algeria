# RULES — Development Rules & Guidelines

> **Version** : 1.0.0  
> **Date** : 2026-07-19  
> **Tech Lead** : Moumen Houma  
> **Domaine** : Modélisation, Optimisation & Aide à la Décision (Master)

---

## 1. General Rules

### 1.1 Code Quality
- **DRY** (Don't Repeat Yourself) : Factoriser tout code dupliqué > 2 fois
- **KISS** (Keep It Simple, Stupid) : Préférer la simplicité à la sophistication inutile
- **Single Responsibility** : Une fonction/classe = une seule raison de changer
- **Type Safety** : Typage strict partout (TypeScript, Python type hints)
- **Test Coverage** : Minimum 80% pour le code métier, 60% pour le code UI

### 1.2 Commit Convention (Conventional Commits)

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

| Type | Usage | Exemple |
|------|-------|---------|
| `feat` | Nouvelle fonctionnalité | `feat(optimization): add warm-start strategy` |
| `fix` | Correction de bug | `fix(osrm): handle timeout on large matrices` |
| `docs` | Documentation | `docs(api): update swagger for v1.2` |
| `style` | Formatage (pas de changement logique) | `style(ui): fix indentation in dashboard` |
| `refactor` | Refactoring | `refactor(solver): extract VRP builder` |
| `perf` | Performance | `perf(cache): add Redis L2 for distance matrices` |
| `test` | Tests | `test(ortools): add benchmark for 100 stops` |
| `chore` | Maintenance | `chore(deps): upgrade OR-Tools to 9.10` |

### 1.3 Branching Strategy (Git Flow Light)

```
main          ──▶ Production (tagged releases)
  │
  ├── develop ──▶ Integration (feature merges)
  │     │
  │     ├── feature/F-123-optimization-warmstart
  │     ├── feature/F-124-rtl-support
  │     └── bugfix/B-456-osrm-timeout
  │
  └── hotfix/H-789-critical-bug ──▶ Direct to main (cherry-pick to develop)
```

### 1.4 Pull Request Rules
- PR title suit Conventional Commits
- Description inclut : What, Why, How
- Minimum 1 review requis (auto-approve pour hotfixes)
- CI/CD doit passer (lint, test, build)
- Pas de merge si conflits non résolus

---

## 2. Backend Rules (Python + FastAPI / Node.js)

### 2.1 Python Rules (Optimization Engine)

```python
# GOOD: Typed, documented, tested
def build_distance_matrix(
    coordinates: list[tuple[float, float]],
    osrm_url: str = "http://localhost:5000",
    cache_ttl: int = 86400,
) -> DistanceMatrix:
    """Build distance matrix from OSRM table API with caching.
    
    Args:
        coordinates: List of (lat, lon) tuples.
        osrm_url: OSRM instance URL.
        cache_ttl: Cache TTL in seconds (default: 24h).
    
    Returns:
        DistanceMatrix: NxN matrix with durations and distances.
    
    Raises:
        OSRMTimeoutError: If OSRM request exceeds 30s.
        InvalidCoordinateError: If coordinates are out of bounds.
    """
    # Implementation
    pass

# BAD: Untyped, undocumented, no error handling
def get_matrix(coords, url):
    r = requests.get(url + "/table", params={"coords": coords})
    return r.json()
```

### 2.2 OR-Tools Integration Rules

```python
# GOOD: Configurable, instrumented, fallback-aware
class VRPSolver:
    def __init__(
        self,
        time_limit_seconds: int = 30,
        first_solution_strategy: int = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
        metaheuristic: int = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
    ):
        self.time_limit = time_limit_seconds
        self.first_strategy = first_solution_strategy
        self.metaheuristic = metaheuristic
    
    def solve(self, problem: VRPProblem) -> VRPSolution:
        """Solve VRP with configured parameters and fallback."""
        try:
            return self._solve_with_ortools(problem)
        except ORToolsTimeoutError:
            logger.warning("OR-Tools timeout, falling back to greedy")
            return self._fallback_greedy(problem)
    
    def _solve_with_ortools(self, problem: VRPProblem) -> VRPSolution:
        # Build model, add constraints, solve
        pass
    
    def _fallback_greedy(self, problem: VRPProblem) -> VRPSolution:
        # Nearest-neighbor + 2-opt
        pass

# BAD: Hardcoded, no fallback, no metrics
solver = pywrapcp.RoutingModel(manager)
solver.Solve()
```

### 2.3 API Rules (FastAPI / Node.js)

```python
# GOOD: Pydantic models, error handling, rate limiting
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Annotated

app = FastAPI()

class OptimizeRequest(BaseModel):
    deliveries: list[Delivery] = Field(..., min_length=1, max_length=500)
    vehicles: list[Vehicle] = Field(..., min_length=1, max_length=50)
    depot: GeoPoint
    constraints: OptimizationConstraints = OptimizationConstraints()

class OptimizeResponse(BaseModel):
    job_id: str
    status: JobStatus
    estimated_duration_ms: int

@app.post("/api/v1/routes/optimize", response_model=OptimizeResponse)
async def optimize_route(
    request: OptimizeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    rate_limit: Annotated[None, Depends(rate_limiter)],
):
    """Submit a route optimization job.
    
    Returns immediately with a job ID. Poll /jobs/{job_id} for results.
    """
    try:
        job = await optimization_service.submit_job(request, current_user.company_id)
        return OptimizeResponse(
            job_id=job.id,
            status=JobStatus.PENDING,
            estimated_duration_ms=estimate_duration(len(request.deliveries)),
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except OptimizationError as e:
        logger.error(f"Optimization failed: {e}")
        raise HTTPException(status_code=500, detail="Optimization engine error")

# BAD: No validation, no types, no error handling
@app.post("/optimize")
def optimize(data):
    result = solve(data)
    return result
```

### 2.4 Database Rules (PostgreSQL + SQLAlchemy)

```python
# GOOD: Migrations, indexes, soft deletes, audit trail
class Delivery(Base):
    __tablename__ = "deliveries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    order_id = Column(String(100), nullable=True)
    address = Column(Text, nullable=False)
    lat = Column(DECIMAL(10, 8), nullable=True)
    lon = Column(DECIMAL(11, 8), nullable=True)
    time_window_start = Column(Time, nullable=True)
    time_window_end = Column(Time, nullable=True)
    weight = Column(DECIMAL(10, 2), default=0)
    volume = Column(DECIMAL(10, 2), default=0)
    priority = Column(Integer, default=1)
    status = Column(String(50), default="pending")
    route_id = Column(UUID(as_uuid=True), ForeignKey("routes.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
    
    __table_args__ = (
        Index('idx_deliveries_company_status', 'company_id', 'status'),
        CheckConstraint('lat BETWEEN -90 AND 90', name='check_lat'),
        CheckConstraint('lon BETWEEN -180 AND 180', name='check_lon'),
    )

# BAD: No indexes, no constraints, no soft delete, no timestamps
class Delivery(Base):
    id = Column(Integer, primary_key=True)
    address = Column(String)
    lat = Column(Float)
    lon = Column(Float)
```

---

## 3. Frontend Rules (React / Vue)

### 3.1 Component Structure

```tsx
// GOOD: Typed, composable, accessible, tested
import { useCallback, useState } from "react";
import { MapPin, Clock } from "lucide-react";
import { DeliveryCardProps } from "./types";

export function DeliveryCard({
  delivery,
  onStatusChange,
  isRTL = false,
}: DeliveryCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const handleToggle = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);
  
  return (
    <article
      className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm"
      dir={isRTL ? "rtl" : "ltr"}
      aria-label={`Delivery ${delivery.id}`}
    >
      <header className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-neutral-900">
          📦 Livraison #{delivery.orderId}
        </h3>
        <button
          onClick={handleToggle}
          aria-expanded={isExpanded}
          aria-label={isExpanded ? "Collapse details" : "Expand details"}
          className="rounded p-1 hover:bg-neutral-100"
        >
          {isExpanded ? "▲" : "▼"}
        </button>
      </header>
      
      <div className="mt-2 space-y-1 text-sm text-neutral-600">
        <div className="flex items-center gap-2">
          <MapPin className="h-4 w-4" aria-hidden="true" />
          <span>{delivery.address}</span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="h-4 w-4" aria-hidden="true" />
          <span>{delivery.timeWindow}</span>
        </div>
      </div>
      
      {isExpanded && (
        <div className="mt-3 border-t border-neutral-100 pt-3">
          <StatusSelector
            currentStatus={delivery.status}
            onChange={onStatusChange}
          />
        </div>
      )}
    </article>
  );
}

// BAD: Untyped, inline styles, no accessibility, no tests
function DeliveryCard(props) {
  return (
    <div style={{border: "1px solid gray", padding: "10px"}}>
      <h3>Delivery #{props.id}</h3>
      <p>{props.address}</p>
      <button onClick={() => alert("clicked")}>Change</button>
    </div>
  );
}
```

### 3.2 State Management

```tsx
// GOOD: Zustand for global state, React Query for server state
import { create } from "zustand";
import { useQuery, useMutation } from "@tanstack/react-query";

// Global UI state (Zustand)
interface UIState {
  sidebarOpen: boolean;
  activeRouteId: string | null;
  toggleSidebar: () => void;
  setActiveRoute: (id: string | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: false,
  activeRouteId: null,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setActiveRoute: (id) => set({ activeRouteId: id }),
}));

// Server state (React Query)
export function useOptimizationJob(jobId: string) {
  return useQuery({
    queryKey: ["optimization", jobId],
    queryFn: () => fetchJobStatus(jobId),
    refetchInterval: (data) => 
      data?.status === "completed" || data?.status === "failed" ? false : 2000,
    staleTime: 0,
  });
}

// BAD: useState for everything, no caching, prop drilling
const [jobs, setJobs] = useState([]);
useEffect(() => {
  const interval = setInterval(() => {
    fetch(`/api/jobs/${id}`).then(r => r.json()).then(setJobs);
  }, 1000);
  return () => clearInterval(interval);
}, [id]);
```

### 3.3 Map Integration (MapLibre)

```tsx
// GOOD: Lazy-loaded, error boundary, performance optimized
import { lazy, Suspense } from "react";
import { ErrorBoundary } from "react-error-boundary";

const MapLibreMap = lazy(() => import("./MapLibreMap"));

export function RouteMap({ routes, depot }: RouteMapProps) {
  return (
    <ErrorBoundary
      fallback={<MapErrorFallback />}
      onError={(error) => logger.error("Map error:", error)}
    >
      <Suspense fallback={<MapSkeleton />}>
        <MapLibreMap
          routes={routes}
          depot={depot}
          rtlTextPlugin="/mapbox-gl-rtl-text.js"
          style="/map-style.json"
        />
      </Suspense>
    </ErrorBoundary>
  );
}

// MapLibreMap.tsx
import { useRef, useEffect } from "react";
import maplibregl from "maplibre-gl";

export function MapLibreMap({ routes, depot }: MapLibreMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  
  useEffect(() => {
    if (!mapContainer.current) return;
    
    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: "/map-style.json",
      center: [depot.lon, depot.lat],
      zoom: 12,
    });
    
    mapRef.current = map;
    
    // Add routes
    routes.forEach((route, index) => {
      map.addSource(`route-${index}`, {
        type: "geojson",
        data: route.geometry,
      });
      map.addLayer({
        id: `route-line-${index}`,
        type: "line",
        source: `route-${index}`,
        paint: {
          "line-color": routeColors[index % routeColors.length],
          "line-width": 3,
        },
      });
    });
    
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [routes, depot]);
  
  return <div ref={mapContainer} className="h-full w-full" />;
}
```

---

## 4. DevOps Rules

### 4.1 Docker Rules

```dockerfile
# GOOD: Multi-stage, non-root, minimal, healthcheck
# Backend Dockerfile
FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim AS runtime

RUN groupadd -r appgroup && useradd -r -g appgroup appuser
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# BAD: Single stage, root user, no healthcheck, bloated
FROM python:3.11
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD python main.py
```

### 4.2 CI/CD Rules (GitHub Actions)

```yaml
# GOOD: Parallel jobs, caching, security scanning
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
      - run: pip install -r requirements.txt
      - run: ruff check .
      - run: mypy .
      - run: black --check .

  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
      - run: pip install -r requirements.txt
      - run: pytest --cov=src --cov-report=xml --cov-report=term
      - uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml

  security:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: pypa/gh-action-pip-audit@v1
        with:
          inputs: requirements.txt
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: "fs"
          scan-ref: "."

  build:
    runs-on: ubuntu-latest
    needs: [test, security]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: routeopt/backend:${{ github.sha }}
```

### 4.3 Environment Rules

| Variable | Dev | Staging | Production | Description |
|----------|-----|---------|------------|-------------|
| `DEBUG` | `true` | `false` | `false` | Debug mode |
| `LOG_LEVEL` | `DEBUG` | `INFO` | `WARN` | Logging level |
| `OSRM_URL` | `localhost:5000` | `osrm-staging:5000` | `osrm-prod:5000` | OSRM instance |
| `REDIS_URL` | `localhost:6379` | `redis-staging:6379` | `redis-prod:6379` | Redis instance |
| `DB_URL` | `sqlite:///dev.db` | `postgresql://...` | `postgresql://...` | Database |
| `JWT_SECRET` | `dev-secret` | `staging-secret` | `<vault>` | JWT signing key |
| `SENTRY_DSN` | — | `staging-dsn` | `prod-dsn` | Error tracking |

---

## 5. Testing Rules

### 5.1 Test Pyramid

```
        /\
       /  \
      / E2E \     <- 5% (Cypress/Playwright) — Critical user flows
     /─────────\
    / Integration \  <- 15% (API tests, DB tests) — Service boundaries
   /───────────────\
  /    Unit Tests    \ <- 80% (Jest, pytest) — Functions, components, models
 /─────────────────────\
```

### 5.2 Unit Test Example (Python)

```python
# GOOD: Isolated, fast, deterministic, parameterized
import pytest
from unittest.mock import Mock, patch
from routeopt.optimization import VRPSolver

class TestVRPSolver:
    @pytest.fixture
    def solver(self):
        return VRPSolver(time_limit_seconds=5)
    
    @pytest.fixture
    def simple_problem(self):
        return VRPProblem(
            depot=GeoPoint(36.7538, 3.0588),
            deliveries=[
                Delivery(id="1", lat=36.75, lon=3.06, demand=1),
                Delivery(id="2", lat=36.76, lon=3.07, demand=1),
            ],
            vehicles=[Vehicle(id="v1", capacity=10)],
        )
    
    def test_solve_returns_valid_solution(self, solver, simple_problem):
        solution = solver.solve(simple_problem)
        assert solution is not None
        assert len(solution.routes) == 1
        assert solution.routes[0].total_distance > 0
    
    def test_solve_with_infeasible_problem_raises(self, solver):
        problem = VRPProblem(
            depot=GeoPoint(36.75, 3.06),
            deliveries=[Delivery(id="1", lat=36.75, lon=3.06, demand=100)],
            vehicles=[Vehicle(id="v1", capacity=1)],
        )
        with pytest.raises(OptimizationError, match="infeasible"):
            solver.solve(problem)
    
    @pytest.mark.parametrize("num_stops,expected_time", [
        (10, 1),
        (50, 5),
        (100, 15),
    ])
    def test_solve_performance(self, solver, num_stops, expected_time):
        problem = generate_random_problem(num_stops)
        start = time.time()
        solver.solve(problem)
        elapsed = time.time() - start
        assert elapsed < expected_time
    
    @patch("routeopt.optimization.osrm_client.get_distance_matrix")
    def test_solve_uses_cached_matrix(self, mock_osrm, solver, simple_problem):
        mock_osrm.return_value = DistanceMatrix([[0, 100], [100, 0]])
        solver.solve(simple_problem)
        mock_osrm.assert_called_once()
```

### 5.3 E2E Test Example (Cypress)

```typescript
// GOOD: Realistic, idempotent, data-driven
describe("Route Optimization Flow", () => {
  beforeEach(() => {
    cy.login("test@company.com", "password");
    cy.visit("/dashboard");
  });
  
  it("should optimize a route and display results", () => {
    // Upload CSV
    cy.get('[data-testid="upload-csv"]').attachFile("deliveries.csv");
    cy.get('[data-testid="import-preview"]').should("contain", "45 livraisons");
    
    // Configure vehicles
    cy.get('[data-testid="configure-vehicles"]').click();
    cy.get('[data-testid="vehicle-count"]').clear().type("3");
    cy.get('[data-testid="save-vehicles"]').click();
    
    // Optimize
    cy.get('[data-testid="optimize-button"]').click();
    cy.get('[data-testid="optimization-loading"]').should("be.visible");
    cy.get('[data-testid="optimization-result"]', { timeout: 30000 }).should("be.visible");
    
    // Verify results
    cy.get('[data-testid="total-distance"]').should("contain", "km");
    cy.get('[data-testid="route-map"]').should("be.visible");
    cy.get('[data-testid="export-pdf"]').should("be.enabled");
  });
  
  it("should handle invalid CSV gracefully", () => {
    cy.get('[data-testid="upload-csv"]').attachFile("invalid.csv");
    cy.get('[data-testid="import-error"]').should("contain", "Format invalide");
    cy.get('[data-testid="optimize-button"]').should("be.disabled");
  });
});
```

---

## 6. Documentation Rules

### 6.1 API Documentation (OpenAPI/Swagger)

```yaml
# GOOD: Complete, example-rich, versioned
openapi: 3.1.0
info:
  title: RouteOpt API
  version: 1.0.0
  description: |
    Route optimization API for Algerian logistics.
    
    ## Authentication
    All endpoints require a JWT token in the Authorization header.
    
    ## Rate Limiting
    - Free: 10 req/min
    - Starter: 100 req/min
    - Pro: 1000 req/min
    
    ## Error Codes
    | Code | Description |
    |------|-------------|
    | 400 | Bad Request |
    | 401 | Unauthorized |
    | 429 | Rate Limited |
    | 500 | Internal Error |

paths:
  /api/v1/routes/optimize:
    post:
      summary: Submit optimization job
      description: |
        Submits a route optimization job. Returns immediately with a job ID.
        Poll /jobs/{job_id} for results.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/OptimizeRequest'
            example:
              deliveries:
                - id: "del-001"
                  address: "12 Rue Didouche Mourad, Alger"
                  lat: 36.7538
                  lon: 3.0588
                  timeWindowStart: "09:00"
                  timeWindowEnd: "12:00"
                  weight: 5.2
              vehicles:
                - id: "v-001"
                  capacity: 500
                  depot: { lat: 36.75, lon: 3.06 }
      responses:
        202:
          description: Job accepted
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/OptimizeResponse'
              example:
                jobId: "job-abc123"
                status: "pending"
                estimatedDurationMs: 5000
```

### 6.2 Code Comments

```python
# GOOD: Why, not what. Explain business logic, not syntax.
# The Algerian fuel crisis (2022-2024) means drivers may need to
# refuel mid-route. We add a 15-minute buffer to account for this.
FUEL_CRISIS_BUFFER_MINUTES = 15

# BAD: Comments restating the obvious
x = x + 1  # Increment x by 1
```

---

## 7. Performance Rules

### 7.1 Optimization Engine Performance Budgets

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| Distance matrix build (< 50 stops) | < 2s | > 5s |
| Distance matrix build (< 200 stops) | < 10s | > 30s |
| OR-Tools solve (< 50 stops) | < 5s | > 15s |
| OR-Tools solve (< 200 stops) | < 30s | > 60s |
| API response (non-optimization) | < 200ms | > 500ms |
| Page load (web app) | < 3s | > 5s |
| Time to Interactive (PWA) | < 5s | > 10s |

### 7.2 Profiling Rules

```python
# GOOD: Profile before optimizing, measure impact
import cProfile
import pstats
from io import StringIO

def profile_optimization(problem: VRPProblem) -> None:
    profiler = cProfile.Profile()
    profiler.enable()
    
    solver = VRPSolver(time_limit_seconds=30)
    solution = solver.solve(problem)
    
    profiler.disable()
    
    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.sort_stats("cumtime")
    stats.print_stats(20)
    
    logger.info(f"Optimization profile:\n{stream.getvalue()}")
    
    return solution
```

---

## 8. Security Rules

### 8.1 OWASP Top 10 Checklist

| Risk | Mitigation | Verification |
|------|-----------|-------------|
| Injection | Parameterized queries, input validation | SAST scan |
| Broken Auth | JWT with RS256, rate limiting, MFA | Penetration test |
| Sensitive Data | Encryption at rest (AES-256), TLS 1.3 | SSL Labs scan |
| XXE | Disable XML external entities | SAST scan |
| Broken Access | RBAC, resource-level authorization | Unit tests |
| Misconfig | Security headers, minimal permissions | CIS benchmark |
| XSS | CSP, output encoding, React auto-escape | DAST scan |
| Insecure Deserial | JSON only, no pickle, schema validation | SAST scan |
| Vulnerable Components | Dependabot, Snyk, pip-audit | CI/CD scan |
| Insufficient Logging | Structured logging, audit trail, SIEM | Log review |

### 8.2 Security Headers

```python
# GOOD: Security headers middleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["routeopt.dz", "*.routeopt.dz"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.routeopt.dz"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Custom security headers
@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

---

*Rules enforced via pre-commit hooks, CI/CD, and code review.*
