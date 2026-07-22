"""FastAPI application entrypoint — wires the modular monolith together."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.config import get_settings
from routeopt.core.exceptions import register_exception_handlers
from routeopt.core.health import check_database, check_osrm, check_redis
from routeopt.core.logging import configure_logging
from routeopt.core.middleware import register_middleware
from routeopt.database import get_session
from routeopt.modules.analytics.router import router as analytics_router
from routeopt.modules.auth.router import router as auth_router
from routeopt.modules.dashboard.router import router as dashboard_router
from routeopt.modules.driver.router import router as driver_router
from routeopt.modules.fleet.router import router as fleet_router
from routeopt.modules.integrations.router import router as integrations_router
from routeopt.modules.orders.router import router as orders_router
from routeopt.modules.predictions.router import router as predictions_router
from routeopt.modules.public_api.router import router as public_api_router
from routeopt.modules.routes.router import router as routes_router
from routeopt.modules.territories.router import router as territories_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings.log_level)
    yield


app = FastAPI(
    title="RouteOpt API",
    version="1.0.0",
    description="Route optimization API for Algerian logistics (docs/PRD.md).",
    lifespan=lifespan,
)

register_middleware(app, settings)
register_exception_handlers(app)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(fleet_router, prefix="/api/v1")
app.include_router(routes_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(driver_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")
app.include_router(predictions_router, prefix="/api/v1")
app.include_router(territories_router, prefix="/api/v1")
# Public partner API — key-authed, mounted off /api/public/v1 (F10).
app.include_router(public_api_router, prefix="/api")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Liveness — the process is up."""
    return {"status": "ok", "environment": settings.environment}


@app.get("/health/ready", tags=["health"])
async def readiness(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> JSONResponse:
    """Readiness — dependency connectivity. OSRM is non-fatal (haversine fallback)."""
    db_ok = await check_database(session)
    redis_ok = await check_redis()
    osrm_ok = await check_osrm()
    ready = db_ok and redis_ok
    components = {
        "database": "ok" if db_ok else "down",
        "redis": "ok" if redis_ok else "down",
        "osrm": "ok" if osrm_ok else "unreachable",
    }
    return JSONResponse(
        status_code=200 if ready else 503,
        content={"ready": ready, "components": components},
    )
