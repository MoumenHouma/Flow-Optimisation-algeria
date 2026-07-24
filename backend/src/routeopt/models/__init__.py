"""SQLAlchemy models. Import all here so Alembic autogenerate sees them.

Full normative schema: docs/SCHEMA.md. MVP-core tables are implemented; the
Phase-2 tables (depots, api_keys, delivery_status_history, proof_of_delivery,
audit_log, refresh_tokens) are documented in SCHEMA.md and added as features land.
"""

from routeopt.models.api_key import ApiKey
from routeopt.models.audit_log import AuditLog
from routeopt.models.base import Base
from routeopt.models.cod_payment import CodPayment
from routeopt.models.company import Company
from routeopt.models.delivery import Delivery
from routeopt.models.delivery_status_history import DeliveryStatusHistory
from routeopt.models.depot import Depot
from routeopt.models.fuel_station import FuelStation
from routeopt.models.invoice import Invoice
from routeopt.models.optimization_job import OptimizationJob
from routeopt.models.password_reset import PasswordResetToken
from routeopt.models.proof_of_delivery import ProofOfDelivery
from routeopt.models.refresh_token import RefreshToken
from routeopt.models.route import Route, RouteStop
from routeopt.models.service_time_model import ServiceTimeModel
from routeopt.models.subscription import Subscription
from routeopt.models.territory import Territory
from routeopt.models.user import User
from routeopt.models.vehicle import Vehicle
from routeopt.models.webhook import Webhook

__all__ = [
    "ApiKey",
    "AuditLog",
    "Base",
    "CodPayment",
    "Company",
    "Delivery",
    "DeliveryStatusHistory",
    "Depot",
    "FuelStation",
    "Invoice",
    "OptimizationJob",
    "PasswordResetToken",
    "ProofOfDelivery",
    "RefreshToken",
    "Route",
    "RouteStop",
    "ServiceTimeModel",
    "Subscription",
    "Territory",
    "User",
    "Vehicle",
    "Webhook",
]
