"""FastAPI application entrypoint — wires the modular monolith together."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from routeopt.config import get_settings
from routeopt.core.exceptions import register_exception_handlers
from routeopt.core.logging import configure_logging
from routeopt.core.middleware import register_middleware
from routeopt.modules.auth.router import router as auth_router
from routeopt.modules.fleet.router import router as fleet_router
from routeopt.modules.orders.router import router as orders_router
from routeopt.modules.routes.router import router as routes_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
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


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
