"""Application settings loaded from environment (docs/RULES.md §4.3)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    sentry_dsn: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
