"""Application settings loaded from environment (docs/RULES.md §4.3)."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SECRET = "dev-insecure-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "local"
    debug: bool = True
    log_level: str = "DEBUG"

    # Data layer
    db_url: str = "postgresql+asyncpg://routeopt:routeopt@localhost:5432/routeopt"
    redis_url: str = "redis://localhost:6379/0"

    # External services
    osrm_url: str = "http://localhost:5000"
    nominatim_url: str = "https://nominatim.openstreetmap.org"
    # Nominatim usage policy: identify the client and bias to Algeria (PRD §4.1).
    nominatim_user_agent: str = "RouteOpt/1.0 (+https://routeopt.dz)"
    nominatim_country: str = "dz"
    # Public Nominatim caps at ~1 req/s; a self-hosted instance can set 0.
    nominatim_rate_limit_s: float = 1.0
    geocoding_cache_ttl_s: int = 2_592_000  # 30 days (SCHEMA.md §7, geo:{hash})

    # Object storage
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "routeopt"

    # Auth (docs/ARCHITECTURE.md §5.1)
    jwt_algorithm: str = "RS256"
    jwt_private_key_path: str = "./keys/jwt-private.pem"
    jwt_public_key_path: str = "./keys/jwt-public.pem"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Optimization
    optimize_queue: str = "queue:optimize"
    optimize_time_limit_seconds: int = 30

    # CORS / security
    allowed_origins: list[str] = ["http://localhost:5173"]
    # Symmetric secret used to derive at-rest encryption keys (webhook secrets).
    secret_key: str = _DEV_SECRET

    sentry_dsn: str | None = None

    # Live tracking + notifications (F18)
    notify_queue: str = "queue:notifications"
    live_position_ttl_s: int = 120  # a stale driver position expires after this
    sms_provider: str = "noop"  # noop | log (real SMS/WhatsApp adapters plug in here)
    # Base URL used to build public delivery-tracking links in notifications.
    public_base_url: str = "http://localhost:5173"

    @model_validator(mode="after")
    def _guard_production(self) -> "Settings":
        """Fail fast on insecure defaults outside local/dev (docs/RULES.md §4.3)."""
        if self.environment == "local":
            return self
        problems: list[str] = []
        if self.debug:
            problems.append("debug must be false")
        if self.secret_key == _DEV_SECRET:
            problems.append("secret_key is the insecure default")
        if self.s3_access_key == "minioadmin" or self.s3_secret_key == "minioadmin":
            problems.append("default S3 credentials")
        if any("localhost" in o or "127.0.0.1" in o for o in self.allowed_origins):
            problems.append("localhost in allowed_origins")
        if problems:
            raise ValueError(
                f"Unsafe config for environment='{self.environment}': {', '.join(problems)}"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
