"""SQLAlchemy models. Import all here so Alembic autogenerate sees them.

Full normative schema: docs/SCHEMA.md. MVP-core tables are implemented; the
Phase-2 tables (depots, api_keys, delivery_status_history, proof_of_delivery,
audit_log, refresh_tokens) are documented in SCHEMA.md and added as features land.
"""

from routeopt.models.base import Base
from routeopt.models.company import Company
from routeopt.models.delivery import Delivery
from routeopt.models.delivery_status_history import DeliveryStatusHistory
from routeopt.models.optimization_job import OptimizationJob
from routeopt.models.proof_of_delivery import ProofOfDelivery
from routeopt.models.refresh_token import RefreshToken
from routeopt.models.route import Route, RouteStop
from routeopt.models.user import User
from routeopt.models.vehicle import Vehicle

__all__ = [
    "Base",
    "Company",
    "Delivery",
    "DeliveryStatusHistory",
    "OptimizationJob",
    "ProofOfDelivery",
    "RefreshToken",
    "Route",
    "RouteStop",
    "User",
    "Vehicle",
]
