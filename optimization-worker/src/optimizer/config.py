"""Worker settings (docs/RULES.md §4.3)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    osrm_url: str = "http://localhost:5000"
    optimize_queue: str = "queue:optimize"

    # Time limits by instance size (docs/ARCHITECTURE.md §2.3, RULES §7.1)
    time_limit_small_s: int = 30  # < 50 stops
    time_limit_medium_s: int = 120  # < 200 stops
    time_limit_large_s: int = 300  # >= 200 stops
    decomposition_threshold: int = 200  # cluster above this (ARCHITECTURE §4.1)

    distance_matrix_ttl_s: int = 86400  # 24h (SCHEMA.md §7)


@lru_cache
def get_settings() -> Settings:
    return Settings()
