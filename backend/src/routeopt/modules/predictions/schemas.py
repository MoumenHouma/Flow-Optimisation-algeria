"""Service-time prediction DTOs (F13)."""

from typing import Any

from pydantic import BaseModel


class ModelSummary(BaseModel):
    trained: bool
    sample_count: int
    cohort_count: int
    global_median_s: int
    mae_seconds: float | None
    trained_at: str | None

    @classmethod
    def from_model(cls, m: Any | None) -> "ModelSummary":
        if m is None:
            return cls(
                trained=False,
                sample_count=0,
                cohort_count=0,
                global_median_s=300,
                mae_seconds=None,
                trained_at=None,
            )
        return cls(
            trained=True,
            sample_count=m.sample_count,
            cohort_count=m.cohort_count,
            global_median_s=m.global_median_s,
            mae_seconds=float(m.mae_seconds) if m.mae_seconds is not None else None,
            trained_at=m.trained_at.isoformat(),
        )
