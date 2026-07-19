"""Preprocessing: validate input and optionally cluster large instances.

For > decomposition_threshold deliveries, geographic clustering (K-Means) splits
the problem into sub-problems solved independently then merged (ARCHITECTURE §4.1).
"""

from __future__ import annotations

from optimizer.config import get_settings
from optimizer.models import OptimizationError, VRPProblem

settings = get_settings()


def validate(problem: VRPProblem) -> None:
    if not problem.deliveries:
        raise OptimizationError("infeasible: no deliveries")
    if not problem.vehicles:
        raise OptimizationError("infeasible: no vehicles")
    if problem.respect_capacity:
        total_demand = sum(d.demand for d in problem.deliveries)
        total_capacity = sum(v.capacity for v in problem.vehicles)
        if total_demand > total_capacity:
            raise OptimizationError("infeasible: total demand exceeds fleet capacity")


def needs_decomposition(problem: VRPProblem) -> bool:
    return len(problem.deliveries) >= settings.decomposition_threshold


def cluster(problem: VRPProblem) -> list[VRPProblem]:
    """Split into geographic clusters (K-Means over delivery coordinates)."""
    # TODO: sklearn.cluster.KMeans on (lat, lon); partition vehicles per cluster;
    # return one sub-VRPProblem per cluster (ARCHITECTURE §4.1 Phase 1).
    raise NotImplementedError("geographic clustering for large instances")
