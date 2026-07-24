"""Service-time prediction (F13): train a per-company cohort model from history.

Training pairs each delivery's ``en_route`` event with its terminal
(``delivered``/``failed``) event in ``delivery_status_history`` to get an observed
on-site duration, groups those by cohort, and stores the per-cohort median. At
optimize time ``predict`` fills each delivery's service time from its cohort,
falling back to the global median and finally the 300s default.
"""

import statistics
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from routeopt.models.delivery import Delivery
from routeopt.models.delivery_status_history import DeliveryStatusHistory
from routeopt.models.service_time_model import ServiceTimeModel
from routeopt.modules.predictions.features import (
    DEFAULT_SERVICE_S,
    cohort_key,
    is_valid_duration,
)

_MIN_COHORT_SUPPORT = 3


def predict(model: dict[str, Any], delivery: Delivery) -> int:
    """Predicted service time (seconds) for a delivery from a stored model."""
    cohorts: dict[str, int] = model.get("cohorts", {})
    fallback = int(model.get("global_median_s", DEFAULT_SERVICE_S))
    key = cohort_key(
        float(delivery.lat) if delivery.lat is not None else None,
        float(delivery.lon) if delivery.lon is not None else None,
        delivery.time_window_start,
        delivery.priority,
        float(delivery.weight),
        delivery.address_locale,
    )
    return int(cohorts.get(key, fallback))


class ServiceTimeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _samples(self, company_id: str) -> list[tuple[str, float]]:
        """(cohort_key, observed_duration_s) pairs from en_route → terminal events."""
        cid = uuid.UUID(company_id)
        deliveries = {
            d.id: d
            for d in await self.session.scalars(
                select(Delivery).where(Delivery.company_id == cid, Delivery.deleted_at.is_(None))
            )
        }
        if not deliveries:
            return []

        rows = list(
            await self.session.scalars(
                select(DeliveryStatusHistory)
                .where(
                    DeliveryStatusHistory.delivery_id.in_(list(deliveries.keys())),
                    DeliveryStatusHistory.to_status.in_(("en_route", "delivered", "failed")),
                )
                .order_by(DeliveryStatusHistory.delivery_id, DeliveryStatusHistory.created_at)
            )
        )

        samples: list[tuple[str, float]] = []
        started_at: dict[uuid.UUID, Any] = {}
        for r in rows:
            if r.to_status == "en_route":
                started_at.setdefault(r.delivery_id, r.created_at)
                continue
            start = started_at.get(r.delivery_id)
            if start is None:
                continue
            duration = (r.created_at - start).total_seconds()
            del started_at[r.delivery_id]
            if not is_valid_duration(duration):
                continue
            d = deliveries[r.delivery_id]
            key = cohort_key(
                float(d.lat) if d.lat is not None else None,
                float(d.lon) if d.lon is not None else None,
                d.time_window_start,
                d.priority,
                float(d.weight),
                d.address_locale,
            )
            samples.append((key, duration))
        return samples

    async def train(self, company_id: str) -> ServiceTimeModel:
        samples = await self._samples(company_id)
        durations = [s for _, s in samples]
        global_median = int(round(statistics.median(durations))) if durations else DEFAULT_SERVICE_S

        grouped: dict[str, list[float]] = {}
        for key, dur in samples:
            grouped.setdefault(key, []).append(dur)
        cohorts = {
            key: int(round(statistics.median(durs)))
            for key, durs in grouped.items()
            if len(durs) >= _MIN_COHORT_SUPPORT
        }

        model_json: dict[str, Any] = {"cohorts": cohorts, "global_median_s": global_median}
        mae = (
            round(
                statistics.fmean(
                    abs(cohorts.get(key, global_median) - dur) for key, dur in samples
                ),
                2,
            )
            if samples
            else None
        )

        existing = await self.session.scalar(
            select(ServiceTimeModel).where(ServiceTimeModel.company_id == uuid.UUID(company_id))
        )
        if existing is None:
            existing = ServiceTimeModel(company_id=uuid.UUID(company_id), model=model_json)
            self.session.add(existing)
        existing.model = model_json
        existing.sample_count = len(samples)
        existing.cohort_count = len(cohorts)
        existing.global_median_s = global_median
        existing.mae_seconds = mae
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    async def get_model(self, company_id: str) -> ServiceTimeModel | None:
        model: ServiceTimeModel | None = await self.session.scalar(
            select(ServiceTimeModel).where(ServiceTimeModel.company_id == uuid.UUID(company_id))
        )
        return model
