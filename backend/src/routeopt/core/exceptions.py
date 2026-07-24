"""Domain exceptions and FastAPI handlers (docs/RULES.md §2.3)."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class RouteOptError(Exception):
    """Base class for domain errors."""

    status_code = 500
    detail = "Internal error"


class NotFoundError(RouteOptError):
    status_code = 404
    detail = "Resource not found"


class ValidationError(RouteOptError):
    status_code = 422
    detail = "Validation error"


class OptimizationError(RouteOptError):
    status_code = 500
    detail = "Optimization engine error"


class AuthError(RouteOptError):
    status_code = 401
    detail = "Not authenticated"


class ForbiddenError(RouteOptError):
    # Authenticated but not allowed (wrong role / insufficient scope).
    status_code = 403
    detail = "Forbidden"


class ConflictError(RouteOptError):
    status_code = 409
    detail = "Resource already exists"


class RateLimitError(RouteOptError):
    status_code = 429
    detail = "Rate limit exceeded"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RouteOptError)
    async def _handle(_: Request, exc: RouteOptError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": str(exc) or exc.detail})
